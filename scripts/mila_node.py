from maya import OpenMaya

__all__ = ['MilaNode', 'mila_node', 'mila_copy', 'mila_init', 'mila_move', 'mila_delete', 'mila_enable_node', 'mila_set_solo', 'mila_remove_solo', 'MILA_GROUP_TYPES', 'MILA_COMPONENT_TYPES']

# Python modules
import re

# Maya modules
import maya.cmds as cmds
import maya.OpenMaya as OpenMaya

# Global var
MILA_MULTI_ATTR_NAME = {
                        "mila_layer": "layers",
                        "mila_mix": "components"
                        }

MILA_GROUP_TYPES = set( ["mila_layer", "mila_mix"] )

MILA_COMPONENT_TYPES = [
                            "mila_diffuse_reflection",
                            "mila_diffuse_transmission",
                            "mila_glossy_reflection",
                            "mila_glossy_transmission",
                            "mila_specular_reflection",
                            "mila_specular_transmission",
                            "mila_transparency",
                            "mila_scatter",
                            "mila_emission"
                        ]

MILA_NODES = set( MILA_COMPONENT_TYPES )
MILA_NODES.update( MILA_GROUP_TYPES )
MILA_NODES.add( "mila_material" )

def getDependencyNode( node ):

    sel = OpenMaya.MSelectionList()
    sel.add( str( node ) )
    obj = OpenMaya.MObject()
    sel.getDependNode( 0, obj )

    return OpenMaya.MFnDependencyNode( obj ), obj


class MilaNode( object ):

    callBackData = {}

    def __eq__( self, other ):

        try:
            return self.name() == other.name()
        except AttributeError:
            return False

    def __ne__( self, other ):

        return not self.__eq__( other )

    def __repr__( self ):

        p = self.parent()

        return 'MilaNode("%s", parent="%s", index=%s )' % ( self.name(), p[0], p[1] )

    def __str__( self ):

        return self.name()

    def __hash__( self ):
        return hash( self.name() )

    def __init__( self, _input, parent=None, index=None ):

        self._node, self.obj = getDependencyNode( _input )

        # Test the inputParent and index
        self._parent = None
        self._parent_id = None
        self._parent_mila = None
        if parent and index is not None:
            parent = mila_node( parent )
            if parent.child( index ) == self:
                self._parent = parent
                self._parent_id = index
            else:
                cmds.warning( "Incorrect parent speficied for MilaNode initialisation, parent will be the default one." )

        self._initCallback()

    def _initCallback( self ):

        # We don't need to add a callback on the mila_material node, maya will update the swatch all by itself
        if self.type() == "root":
            return
        # The current node doesn't have callbacks, lets create them
        for item in MilaNode.callBackData:
            if item == self.name():
                return

        MilaNode.callBackData[self.name()] = []
        # Add a callback to trigger an update everytime a connection or an attribute change
        MilaNode.callBackData[self.name()].append( OpenMaya.MNodeMessage.addNodeDirtyCallback( self.obj, self.attrChangeCallback ) )
        # Add a callback to delete all callback when the node is going to be deleted
        MilaNode.callBackData[self.name()].append( OpenMaya.MNodeMessage.addNodePreRemovalCallback( self.obj, self.deleteCallback ) )


    def attrChangeCallback( self, node, plug, *args ):

        # Refresh the parent mila node if any
        for parent in self.parentMila():
            mila_refresh_swatch( parent )


    def deleteCallback( self, *args ):
        
        try:
            for callback in MilaNode.callBackData[self.obj]:
                OpenMaya.MMessage.removeCallback( callback )
        except KeyError:
            pass

        try:
            del MilaNode.callBackData[self.obj]
        except KeyError:
            pass

    def type( self ):
        if self.nodeType() == "mila_material":
            return "root"
        elif self.nodeType() in MILA_GROUP_TYPES:
            return "group"
        elif self.nodeType() in MILA_COMPONENT_TYPES:
            return "component"
        else:
            return None
        
    def select(self):
        cmds.select(self.name())

    def nodeType( self ):
        return self._node.typeName()

    def name( self ):
        return self._node.name()

    def parentMila( self ):
        return list( set( self._findParentMilaRecurse() ) )

    def _findParentMilaRecurse( self ):

        for parent in self.parents():
            if parent.type() == "root":
                yield parent
            else:
                for item in parent._findParentMilaRecurse():
                    yield item

    def isUsedMultipleTimes( self ):
        # We look for multiple elements in self.parents() and self.parentMila()
        # Both function are generators, so we will stop as soon as possible

        usage = 0

        for item in self.parents():
            usage += 1
            # If we reach here, we already found two parents, this node is used multiple times
            if usage > 1:
                return True

        usage = 0
        for item in self.parentMila():
            usage += 1
            # If we reach here, this node is used in at least two mila network
            if usage > 1:
                return True

        return False

    def child( self, index=0 ):

        if self.type() == "component":
            return None
        node = self.source( self.inAttr( index ) )
        if node:
            node._parent = self
            node._parent_id = index
            return node

        return None

    def connectedIndices( self ):
        out = []
        for index in self.indices():
            if cmds.connectionInfo( self.inAttr( index ), isExactDestination=True ):
                out.append( index )
        return out

    def indices( self ):
        return cmds.getAttr( self.multiAttr(), multiIndices=True ) or []

    def children( self, index=False, recurse=False ):

        if self.type() == "component":
            return

        if self.type() == "root":
            pass

        sparse_indices = self.indices()

        for i in sparse_indices:
            inputItem = self.source( self.inAttr( i ) )
            if inputItem:
                if recurse:
                    for child in MilaNode( inputItem ).children( recurse=True ):
                        if index:
                            yield MilaNode( child, self, i ), i
                        else:
                            yield MilaNode( child, self, i )

                if index:
                    yield MilaNode( inputItem, self, i ), i
                else:
                    yield MilaNode( inputItem, self, i )

    def parent( self ):

        all_parents = self.parents()

        if self._parent in all_parents:
            return self._parent, self._parent_id
        else:
            for parent, index in self.parents( returnIndex=True ):
                return parent, index

        return None, None

    def parents( self, returnIndex=False ):

        for node, plug in self.destinations( self.outAttr(), plug=True ):
            if node:
                if returnIndex:
                    if node.type() == "root":
                        yield node, None
                    else:
                        pattern = r'%s\[([0-9]*)\]' % node._multiAttrName()
                        index = int( re.findall( pattern, plug )[0] )
                        yield node, index
                else:
                    yield node

    def soloItem( self ):
        """Only Work for mila_material node, return the solo item if any"""
        if self.type() != "root":
            return None

        tmp_layer = self.soloLayer()
        if tmp_layer:
            solo_node = tmp_layer.source( tmp_layer.inAttr( 0 ) )
            if solo_node:
                return solo_node
        return None

    def soloLayer( self ):
        if self.type() != "root":
            return None

        tmp_layer = self.source( self.inAttr() )
        if cmds.objExists( tmp_layer.attr( "tmp_layer" ) ):
            return tmp_layer
        return None


    def index( self, inputNode ):
        """ Return the index in the multiAttr array where the child is connected
        If the inputNode is on a child return None """

        for child, index in self.children( index=True ):
            if child == inputNode:
                return index

    def outAttr( self ):
        return "%s.message" % self.name()

    def inAttr( self, index=None ):
        if self.type() == "group":
            return "%s.shader" % self.multiAttr( index )
        elif self.type() == "root":
            return "%s.shader" % self
        return ""

    def attr( self, attr ):
        return "%s.%s" % ( self.name(), attr )

    def source( self, attr ):
        attribute = ""
        if "." in attr:
            attribute = attr
        else:
            attribute = self.attr( attr )
        return mila_node( cmds.connectionInfo( attribute, sourceFromDestination=True ) )

    def destinations( self, attr, plug=False ):
        attribute = ""
        if "." in attr:
            attribute = attr
        else:
            attribute = self.attr( attr )
        connected_plugs = cmds.connectionInfo( attribute, destinationFromSource=True ) or []
        return_value = []
        for item in connected_plugs:
            if plug:
                return_value.append( ( mila_node( item ), item ) )
            else:
                return_value.append( mila_node( item ) )
        return return_value

    def shaderSaveAttr( self ):
        if not cmds.objExists( self.attr( "save_shader" ) ):
            cmds.addAttr( self, longName="save_shader", at="message" )

        return self.attr( "save_shader" )


    def multiAttr( self, index=None, child=None ):

        if child:
            id = self.index( child )
            if id is not None:
                index = id

        if index is not None:
            index = "[%s]" % index
        else:
            index = ""
        return "%s.%s%s" % ( self.name(), self._multiAttrName(), index )


    def _multiAttrName( self ):

        if self.type() == "group":
            return MILA_MULTI_ATTR_NAME[self.nodeType()]

        return ""


    def attrData( self, index=0 ):

        if self.type() != "group":
            return {}

        dataDict = {}

        # We skip the first two attibutes, the first is the multi itself, and the second is the shader input connection
        for attr in cmds.listAttr( self.multiAttr( index ), multi=True )[2:]:
            attr = attr.split( "." )[-1]
            dataDict[attr] = get_connection_or_value( self.multiAttr( index ) + "." + attr )

        return dataDict


    def setAttrData( self, data, index=0 ):

        if self.type() != "group" or not data:
            return

        for attr in data:
            if cmds.objExists( self.multiAttr( index ) + "." + attr ):
                set_connection_or_value( self.multiAttr( index ) + "." + attr, data[attr] )


    def niceName( self ):

        if cmds.objExists( "%s.%s" % ( self.name(), "mila_nice_name" ) ):
            niceName = str( cmds.getAttr( "%s.%s" % ( self.name(), "mila_nice_name" ) ) ).strip()

            if niceName:
                return niceName

        return self.name()


    def setNiceName( self, newName ):

        if not cmds.objExists( "%s.%s" % ( self.name(), "mila_nice_name" ) ):
            cmds.addAttr( self.name(), longName="mila_nice_name", dt="string" )

        cmds.setAttr( "%s.%s" % ( self.name(), "mila_nice_name" ), str( newName ).strip(), type="string" )

    def enabled( self ):
        parent_node, index = self.parent()
        if parent_node:
            return cmds.getAttr( parent_node.multiAttr( index ) + ".on" )
        else:
            return False

def mila_refresh_swatch( node ):
    # Set a value to force refresh
    # This will fail if the show_framebuffer attribut has an input connection but it is very unlikely that someone will try to connect something to this

    if not cmds.objExists( node ):
        return

    cmds.dgdirty( node.inAttr() )
    

def mila_flatten_node_selection( node_list_in ):
        """
        Given a list of MilaNode, return only the top level items (ignore any child if their parent is in the list)
        """
        node_list = []
        for node in node_list_in:
            n = mila_node( node )
            if n:
                node_list.append( n )

        new_set = set( node_list )

        for node in node_list:
            new_set -= set( node.children( recurse=True ) )

        return new_set
    

def mila_node( input_, parent=None, index=None, create=False, name="" ):

    if input_ is None:
        return None

    if isinstance( input_, MilaNode ):
        return input_

    # elif cmds.nodeType( input_ ) in mil_group_types or input_ in MILA_COMPONENT_TYPES:
    if cmds.objExists( input_ ) and cmds.nodeType( input_ ) in MILA_NODES:
        return MilaNode( input_, parent, index )
    elif create and input_ in MILA_NODES:
        kargs = {}
        if name:
            kargs["name"] = name
        node = cmds.createNode( input_, skipSelect=True, **kargs )
        cmds.connectAttr( "%s.message" % node, "defaultRenderUtilityList1.utilities", nextAvailable=True )
        return MilaNode( node )
    else:
        return None
    
def mila_copy( node ):

    new_node = cmds.duplicate( node, upstreamNodes=True )[0]
    return mila_node( new_node )
    

def get_connection_or_value( attribute ):
    
    connection = cmds.connectionInfo( attribute, sourceFromDestination=True )
    if connection:
        return connection
    else:
        try:
            attr_value = cmds.getAttr( attribute )
        except RuntimeError:
            return None
        if type( attr_value ) == list:  # color (eg, tint) is returned in list of tuple, [(r,g,b)]
            attr_value = attr_value[0]
        return attr_value


def set_connection_or_value( attr, value ):

    if value is None:
        return

    if isinstance( value, ( str, unicode ) ) and cmds.objExists( value ):
        try:
            cmds.connectAttr( value, attr, f=True )
        except RuntimeError, e:
            if "Data types of source and destination are not compatible" in str( e ):
                pass
            else:
                raise
    else:
        attr_type = cmds.getAttr( attr, type=True )
        try:
            if attr_type in ( 'double3', 'float3' ):  # value returned is a list of one tuple, ie [(r,g,b)]
                cmds.setAttr( attr, *value, type=attr_type )
            elif attr_type == "string":
                cmds.setAttr( attr, value, type=attr_type )
            else:
                cmds.setAttr( attr, value )
        except RuntimeError, e:
            if "locked or connected" in str( e ):
                pass
            else:
                raise


def mila_init( node ):

    root_layer = ""

    if not cmds.connectionInfo( "%s.shader" % node, isExactDestination=True ):
        # Create the top level hidden mila_layer
        root_layer = cmds.createNode( "mila_layer", name="%s_root_layer" % node, skipSelect=True )

        cmds.connectAttr( "%s.message" % root_layer, "%s.shader" % node, force=True )

    else:
        # Something is connected, use it as root
        root_layer = cmds.connectionInfo( "%s.shader" % node, sourceFromDestination=True ).split( "." )[0]

    return root_layer


def mila_get_input( node, parent=None, index=None ):

    node = mila_node( node )
    parent = mila_node( parent )

    if parent and index:
        return node, parent, index

    if not ( parent and index ):
        parent, index = node.parent()
    elif parent:
        parent = mila_node( parent )
        index = parent.index( node )
    elif index:
        parent, null = node.parent()

    return node, parent, index


def mila_enable_node( node, parent=None, index=None, value=True ):
    node, parent, index = mila_get_input( node, parent, index )

    if parent:
        return cmds.setAttr( parent.multiAttr( index ) + ".on", value )


def mila_delete( node, parent=None, index=None, force=False, clean=True ):

    node, parent, index = mila_get_input( node, parent, index )

    multiConnection = False
    if node.isUsedMultipleTimes():
        multiConnection = True
    # Disconnecting the node from its parent
    node, null = mila_remove_node( parent, index )

    if clean:
        # Reorder and Clean the parent (to remove empty slots)
        mila_reorder_node( parent, clean=True )

    if force or not multiConnection or not node.parents():
        # Deleting all child of the node
        for child, null in node.children( index=True ):
            mila_delete( child, clean=False )
        # Now delete the node
        cmds.delete( node )


def mila_get_node( parent=None, index=None ):
    """ get the node from the destination with the previous Data it had on its parent"""
    
    parent = mila_node( parent )
    node = parent.child( index )
    
    attrData = parent.attrData( index )

    return node, attrData


def mila_remove_node( parent=None, index=None ):
    """ remove the node from the destination """
    parent = mila_node( parent )
    
    node = parent.child( index )
    attrData = parent.attrData( index )

    # Disconnect the node
    cmds.disconnectAttr( node.outAttr(), parent.inAttr(index) )

    # Delete the item
    cmds.removeMultiInstance( parent.multiAttr( index ), b=True )

    return node, attrData


def mila_set_solo( node, mila=None ):

    # Create temp custom attribute on the mila to store the original graph
    # Create a new empty layer to old the solo item and connect it to the shader attribute
    # Connect the component into the new layer
    node = mila_node( node )

    if mila is None:
        for item in node.parentMila():
            mila = item
            break
    else:
        mila = mila_node( mila )

    if not mila:
        return

    # Some other node might be already solo, if so, only replace it
    if cmds.connectionInfo( mila.shaderSaveAttr(), isExactDestination=True ):
        tmp_layer = mila_node( cmds.connectionInfo( mila.inAttr(), sourceFromDestination=True ) )
        if cmds.objExists( tmp_layer.attr( "tmp_layer" ) ):
            # The layer in the mila is a solo layer, juste use it
            cmds.connectAttr( node.outAttr(), tmp_layer.inAttr( 0 ), force=True )

    else:
        # Connect the root layer to the save_shader attr
        cmds.connectAttr( mila.child().outAttr(), mila.shaderSaveAttr(), force=True )

        # Create an empty layer
        tmp_layer = mila_node( "mila_layer", name="%s_solo_layer" % mila.name() )
        cmds.addAttr( tmp_layer, longName="tmp_layer", at="message" )
        # Connect the solo node to the shader attribute of the mila
        cmds.connectAttr( node.outAttr(), tmp_layer.inAttr( 0 ), force=True )
        cmds.connectAttr( tmp_layer.outAttr(), mila.inAttr(), force=True )


def mila_remove_solo( mila ):

    mila = mila_node( mila )

    if cmds.connectionInfo( mila.shaderSaveAttr(), isExactDestination=True ):
        # There is something to restore
        # Get what is in the shader slot and delete it
        tmp_layer = mila_node( cmds.connectionInfo( mila.inAttr(), sourceFromDestination=True ) )
        if cmds.objExists( tmp_layer.attr( "tmp_layer" ) ):
            cmds.delete( tmp_layer )

        orig_layer = mila_node( cmds.connectionInfo( mila.shaderSaveAttr(), sourceFromDestination=True ) )

        cmds.connectAttr( orig_layer.outAttr(), mila.inAttr(), force=True )
        cmds.disconnectAttr( orig_layer.outAttr(), mila.shaderSaveAttr() )

def mila_clean( node, indices=None ):
    # Remove all empty entry in the node

    node = mila_node( node )
    if indices is None:
        indices = node.indices()

    for i in indices:
        if not node.child( i ):
            cmds.removeMultiInstance( node.multiAttr( i ), b=True )


def mila_move_force( source, dest, index=None, nodeData=None, remove=False ):
    # Remove the source from its parent and connect it to the index in the specified destination.
    # The connection will be forced. Anything connected to the destination will be discarded.
    # If nodeData is specified use it, else use the data from the node's parent
    source = mila_node( source )
    dest = mila_node( dest )

    parent, parent_id = source.parent()

    if parent:
        if remove:
            source, sourceData = mila_remove_node( parent, parent_id )
        else:
            source, sourceData = mila_get_node( parent, parent_id )
    else:
        sourceData = nodeData

    cmds.connectAttr( source.outAttr(), dest.inAttr( index ), force=True )
    if sourceData:
        dest.setAttrData( sourceData, index )


def mila_reorder_node( parent, nodes=None, startingIndex=0, remove=True, clean=False ):
    # We need to make all node to start at startingIndex and follow consecutively
    parent = mila_node( parent )

    # Get a list of all indices in the node to clean anything left empty
    origIndices = parent.indices()

    if nodes is None:
        nodes = parent.children()
    else:
        nodes = [mila_node( node ) for node in nodes]

    node_id_data = []

    for node in nodes:
        p, index = node.parent()
        node, data = mila_get_node( p, index )
        node_id_data.append( ( node, index, data ) )

    i = startingIndex
    for node, index, data in node_id_data:
        if index != i:
            mila_move_force( node, parent, index=i, nodeData=data, remove=remove )
        i += 1

    if clean and origIndices:
        # Clean all possible empty slot
        # we will range from the index 0, to the last possible index. It can be either the orginal last index; or the new last index
        mila_clean( parent, range( max( i, origIndices[-1] ) + 1 ) )

    return i

def mila_move( sources, dest, index=0, remove=False ):  # , reordering=False):
    # Move all items to the specified index inside the desdtination
    # Everything will be reorganized so that each group node wil have its first item at index 0 and everything stacked consecutively without hole

    pending_nodes = []
    parent_for_cleaning = set()

    # If we specify remove=False, the source node won't be disconnected from their current position.
    if remove:
        # First, remove all sources so we make some room for reodering
        # Keep track of their foreign parent to clean them at the end
        for node in sources:
            node_parent, parent_id = node.parent()
            if node_parent and parent_id is not None:
                if node_parent != dest:
                    parent_for_cleaning.add( node_parent )
                pending_nodes.append( mila_remove_node( node_parent, parent_id ) )
            else:
                pending_nodes.append( ( node, {} ) )
    else:
        # We don't remove the node from their original position
        for node in sources:
            node_parent, parent_id = node.parent()
            if node_parent:
                pending_nodes.append( mila_get_node( node_parent, parent_id ) )
            else:
                pending_nodes.append( ( node, {} ) )

    # We are moving the source nodes to the specified index
    # Before we can do any work, we need to plan all moves to be as efficient as possible

    before_nodes = []
    after_nodes = []
    for child, child_id  in dest.children( index=True ):
        if child_id < index:
            before_nodes.append( child )
        else:
            after_nodes.append( mila_remove_node( dest, child_id ) )

    if remove and before_nodes and node.parent()[0]:
        # We are doing a move, if the node comes from the top of the layers we need to reorder all nodes before the dest index
        lastIndex = mila_reorder_node( dest, before_nodes, 0 )
    else:
        # We don't remove any node, the stack on top of the destination cannot be dirty, we don't reorder
        lastIndex = index

    # Now put the sources in the gap created earlier
    i = lastIndex
    if pending_nodes:
        for node, data in pending_nodes:
            mila_move_force( node, dest, index=i, nodeData=data, remove=remove )
            i += 1
        lastIndex = i

    # Now add all after nodes
    for node, data in after_nodes:
        mila_move_force( node, dest, index=i, nodeData=data, remove=False )
        i += 1

    # Now clean all modified foreign group
    for node in parent_for_cleaning:
        mila_reorder_node( node, clean=True )
