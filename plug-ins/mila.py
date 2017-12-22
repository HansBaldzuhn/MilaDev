import sys
import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx

from mila_node import *

import pprint
from multiprocessing.dummy import active_children


def sysPrint( truc ):
    sys.__stdout__.write( "%s\n" % truc )


kMoveFlag = "-m"
kMoveLongFlag = "-move"

kSoloFlag = "-so"
kSoloFlagLong = "-solo"

kRemoveSoloFlag = "-rso"
kRemoveSoloFlagLong = "-removeSolo"

kDeleteFlag = "-del"
kDeleteFlagLong = "-delete"

kSourceFlag = "-s"
kSourceFlagLong = "-source"

kDestinationFlag = "-d"
kDestinationFlagLong = "-destination"

kNodeFlag = "-n"
kNodeFlagLong = "-node"

kParentFlag = "-p"
kParentFlagLong = "-parent"

kIndexFlag = "-i"
kIndexFlagLong = "-index"

kKeepFlag = "-k"
kKeepFlagLong = "-keep"

kForceFlag = "-f"
kForceFlagLong = "-force"

kEnableNodeFlag = "-e"
kEnableNodeFlagLong = "-enable"

kValueFlag = "-v"
kValueFlagLong = "-value"

kPlugDict = "plugs"
kValueDict = "values"


class Action():
    kNothing = -1
    kMove = 0  # use: -move -source "node_name" [multi] -destination "node_name" -index int
    kDelete = 1  # use: -delete -node "node_name" (-parent "node_name") (-index int) -force bool
    kSolo = 2  # use: -solo -node "node_name" -parent "node_name"
    kRemoveSolo = 3  # use: -solo -parent "node_name"
    kEnable = 4  # use: -enable -node "node_name" (-parent "node_name") (-index int) -value bool


class milaMaterial( OpenMayaMPx.MPxCommand ):

    def __init__( self ):
        OpenMayaMPx.MPxCommand.__init__( self )

        self.sources = []
        self.destination = None

        self.node = ""
        self.parent = None

        self.index = None

        self.value = 0.0

        self.keep = False

        self.force = False

        self.action = Action.kNothing

        self.dgModifier = OpenMaya.MDGModifier()
        self.sel = OpenMaya.MSelectionList()

    @staticmethod
    def creator():
        return OpenMayaMPx.asMPxPtr( milaMaterial() )

    def doIt( self, argList ):

        sysPrint( "\n########" )

        sysPrint( "arglist size: %s" % argList.length() )

        for i in range( argList.length() ):
            sysPrint( "argList: %s" % argList.asString( i ) )

        try:
            argParser = OpenMaya.MArgParser( self.syntax(), argList )
        except Exception, e:
            sysPrint( "Error parsing syntax" )
            raise AttributeError( "Wrong argument call: %s" % str( e ) )

        if argParser.isFlagSet( kSoloFlag ):
            # use: -solo -node "node_name" -parent "node_name"
            self.action = Action.kSolo

            if argParser.isFlagSet( kNodeFlag ):
                return

            self.node = argParser.flagArgumentString( kNodeFlag, 0 )
            if argParser.isFlagSet( kParentFlag ):
                self.parent = argParser.flagArgumentString( kParentFlag, 0 )

        elif argParser.isFlagSet( kRemoveSoloFlag ):
            # use: -removeSolo -parent "node_name"
            self.action = Action.kRemoveSolo

            if not argParser.isFlagSet( kNodeFlag ):
                return

            self.node = argParser.flagArgumentString( kNodeFlag, 0 )

        elif argParser.isFlagSet( kDeleteFlag ):
            # use: -delete -node "node_name" (-parent "node_name") (-index int) -force int
            self.action = Action.kDelete

            if not argParser.isFlagSet( kNodeFlag ):
                sysPrint( "missing argument -node" )
                return

            self.node = argParser.flagArgumentString( kNodeFlag, 0 )
            if argParser.isFlagSet( kParentFlag ):
                self.parent = argParser.flagArgumentString( kParentFlag, 0 )
            if argParser.isFlagSet( kIndexFlag ):
                self.index = argParser.flagArgumentString( kIndexFlag, 0 )
            if argParser.isFlagSet( kForceFlag ):
                self.force = argParser.flagArgumentBool( kForceFlag, 0 )

        elif argParser.isFlagSet( kEnableNodeFlag ):
            # use: -enable -node "node_name" (-parent "node_name") (-index int) -value int

            self.action = Action.kEnable

            if not argParser.isFlagSet( kNodeFlag ):
                sysPrint( "missing argument -node" )
                return

            self.node = argParser.flagArgumentString( kNodeFlag, 0 )
            if argParser.isFlagSet( kParentFlag ):
                self.parent = argParser.flagArgumentString( kParentFlag, 0 )
            if argParser.isFlagSet( kIndexFlag ):
                self.index = argParser.flagArgumentString( kIndexFlag, 0 )

        elif argParser.isFlagSet( kMoveFlag ):
            # use: -move -source "node_name" [multi] -destination "node_name" -index int
            sysPrint( "We need to move !" )

            self.action = Action.kMove

            if not ( argParser.isFlagSet( kSourceFlag ) and argParser.isFlagSet( kDestinationFlag ) ):
                sysPrint( "not enougth argument" )
                return

            for i in range( argParser.numberOfFlagUses( kSourceFlag ) ):
                arg = argParser.flagArgumentString( kSourceFlag, i )
                self.sources.append( arg )

            dest_arg = argParser.flagArgumentString( kDestinationFlag, 0 )
            index_arg = argParser.flagArgumentInt( kIndexFlag, 0 )

            self.destination = dest_arg
            self.index = index_arg

            self.keep = argParser.isFlagSet( kKeepFlag )

        else:
            sysPrint( "Nohting to do" )

        self.redoIt()

    def redoIt( self, *args ):

        if self.action == Action.kMove:

            sources = []

            for item in self.sources:
                node = mila_node( item )
                if not node:
                    raise AttributeError( "%s is not a valid mila node" % item )
                sources.append( node )

            destination = mila_node( self.destination )

            if not self.destination:
                raise AttributeError( "Source and/or destination is not a valid mila node." )

            self.move( sources, destination, self.index, self.keep )

        if self.action == Action.kEnable:

            node, parent, index = self.get_input( self.node, self.parent, self.index )
            if parent:
                self.dgModifier.newPlugValueBool( self._get_MPlug( parent.multiAttr( index ) + ".on" ), self.value )

        elif self.action == Action.kDelete:
            self.delete_node( self.node, self.parent, self.index, self.force )

        elif self.action == Action.kSolo:
            self.set_solo( self.node, self.parent )

        elif self.action == Action.kRemoveSolo:
            self.remove_solo( self.parent )

        self.dgModifier.doIt()

    def undoIt( self, *args ):

        self.dgModifier.undoIt()
        # Reset the dgModifier, all the data we need are stored in the object and not doing so breaks the redo (I don't know why ...)
        self.dgModifier = OpenMaya.MDGModifier()

    def isUndoable( self, *args ):
        return True

    def _get_MPlug( self, *args ):

        outputs = []
        self.sel.clear()
        for item in args:
            self.sel.add( item )

        for i in range( self.sel.length() ):
            p = OpenMaya.MPlug()
            self.sel.getPlug( i, p )
            outputs.append( p )
        if len( outputs ) > 1:
            return outputs
        else:
            return outputs[0]

    def get_input( self, node, parent=None, index=None ):

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

    def removeMultiInstance( self, node, index ):
        cmd = "removeMultiInstance -b true %s" % node.multiAttr( index )
        OpenMaya.MGlobal.executeCommand( cmd )

    def set_solo( self, node, mila=None ):

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

        # Get saveShader Attribute

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

    def remove_solo( self, mila ):

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

    def delete_node( self, node, parent=None, index=None, force=False ):

        node, parent, index = self.get_input( node, parent, index )

        multiConnection = False
        if node.isUsedMultipleTimes():
            multiConnection = True
        # Disconnecting the node from its parent
        node, null_data = self.get_node( parent, index )

        # Reorder and Clean the parent (to remove empty slots)
        self.reorder_node( parent, clean=True )

        if force or not multiConnection or not node.parents():
            # Deleting all child of the node
            for child, null in node.children( index=True ):
                self.delete_node( child, clean=False )
            # Now delete the node
            self.dgModifier.deleteNode( node.obj )

    def disconnect( self, source, destination ):

        print "disconnect: %s, %s" % ( source, destination )
        sourcePlug, destPlug = self._get_MPlug( source, destination )

        self.dgModifier.disconnect( sourcePlug, destPlug )

    def connect( self, source, destination ):
        print "connect: %s, %s" % ( source, destination )

        sourcePlug, destPlug = self._get_MPlug( source, destination )
        self.dgModifier.connect( sourcePlug, destPlug )

    def objExists( self, input ):

        sel = OpenMaya.MSelectionList()

        try:
            sel.add( input )
        except RuntimeError, e:
            if "kInvalidParameter" in str( e ):
                return False
        else:
            raise

        return True

    def set_node_data( self, node, data, index=0 ):

        if not data:
            return

        # Get a plug to the correct index parent plug

        multi_plug = self.get_multi_plug( node.obj )

        parentPlug = multi_plug.elementByLogicalIndex( index )
        plugDict = {}
        for i in range( parentPlug.numChildren() ):
            plug = parentPlug.child( i )

            if plug.isCompound():
                for i in range( plug.numChildren() ):
                    childPlug = plug.child( i )
                    attributeName = OpenMaya.MFnAttribute( childPlug.attribute() ).name()
                    plugDict[attributeName] = childPlug

            attributeName = OpenMaya.MFnAttribute( plug.attribute() ).name()
            plugDict[attributeName] = plug
            toto = OpenMaya.MPlug()

        print "SET DATA:"
        pprint.pprint( plugDict )

        # First set all Plug value
        for attributeName, value in data[kValueDict]:

            sysPrint( "setting: %s" % attributeName )

            if not attributeName in plugDict:
                continue

            plug = plugDict[attributeName]

            if plug.isCompound():
                # Never set compound plug
                continue

            sysPrint( "Set Value %s : %s" % ( plug.name(), value ) )
            self.dgModifier.newPlugValueDouble( plug, value )

        self.dgModifier.doIt()

        # Now Connect all plugs
        for attributeName, node, attribute in data[kPlugDict]:

            sysPrint( "connecting: %s" % attributeName )

            if not attributeName in plugDict:
                continue

            sysPrint( "getting plug from dict" )
            plug = plugDict[attributeName]
            sysPrint( "plug: %s" % plug.name() )

            source_plug = OpenMaya.MPlug( node, attribute )
            sysPrint( "sourceplug: %s" % source_plug.name() )

            sysPrint( "Connect %s : %s" % ( source_plug.name(), plug.name() ) )
            self.dgModifier.connect( source_plug, plug )

        self.dgModifier.doIt()

    def clean( self, node, indices=None ):
        # Remove all empty entry in the node

        node = mila_node( node )
        if indices is None:
#             print "node %r, attr %s" % (node, node.multiAttr())
            indices = node.indices()

        for i in indices:
            if not node.child( i ):
                self.removeMultiInstance( node, i )

    def get_multi_plug( self, obj ):

        fn = OpenMaya.MFnDependencyNode( obj )

        try:
            return fn.findPlug( "components" )
        except Exception, e:
            if "kInvalidParameter" in str( e ):
                return fn.findPlug( "layers" )
            else:
                raise

    def get_node( self, parent=None, index=None, keep=False ):
        print "get_node: %s at %s" % ( parent, index )

        def getValue( inputPlug ):
            return inputPlug.asDouble()
    #         try:
    #         except Exception, e:
    #             if "kInvalidParameter" in str(e):
    #                 pass
    #             else:
    #                 raise
    #         try:
    #             return inputPlug.asBool()
    #         except:
    #             raise

        # Remove the node from the destination
        parent = mila_node( parent )

        multiPlug = self.get_multi_plug( parent.obj )

        multiPlugIndex = multiPlug.elementByLogicalIndex( index )

        data = { kPlugDict:[], kValueDict: [] }

        # Get Data for all elements of the compound array plug
        for i in range( multiPlugIndex.numChildren() ):
            plug = multiPlugIndex.child( i )
            attribute = OpenMaya.MFnAttribute( plug.attribute() ).name()

            if attribute == "shader":
                # Skip this one, it should not be handled here
                continue

            compoundPlugArray = OpenMaya.MPlugArray()
            compoundConnected = plug.connectedTo( compoundPlugArray, True, False )

            # First, check if we have a compound plug
            # We do not want to get the value of a compound plug, it has no meaning
            # we will get value/connection of all its child
            plugArray = OpenMaya.MPlugArray()
            if plug.isCompound():
                # Loop on all Child
                for i in range( plug.numChildren() ):
                    childPlug = plug.child( i )
#                     childPlugName = childPlug.partialName( False, False, False, True, False, True)
                    childAttribute = OpenMaya.MFnAttribute( childPlug.attribute() ).name()

                    if childPlug.connectedTo( plugArray, True, False ):
                        data[kPlugDict].append( ( childAttribute, plugArray[0].node(), plugArray[0].attribute() ) )
                        # now disconnect it
                        self.dgModifier.disconnect( plugArray[0], childPlug )
                    else:
                        data[kValueDict].append( ( childAttribute, getValue( childPlug ) ) )
            elif not compoundConnected:
                # Input is not a compount
                data[kValueDict].append( ( attribute, getValue( plug ) ) )

            # we still need to check for connection to the compound plug
            if compoundConnected:
                data[kPlugDict].append( ( attribute, compoundPlugArray[0].node(), compoundPlugArray[0].attribute() ) )
                # now disconnect it
                self.dgModifier.disconnect( compoundPlugArray[0], plug )

        node = parent.child( index )
        if node and not keep:
            self.disconnect( node.outAttr(), parent.inAttr( index ) )

        print "DATA:"
        pprint.pprint( data )

        return node, data

    def remove_node( self, parent=None, index=None ):
        """ remove the node from the destination """
        parent = mila_node( parent )

        node = parent.child( index )
        attrData = parent.attrData( index )

        # Disconnect the node
        cmds.disconnectAttr( node.outAttr(), parent.inAttr( index ) )

        # Disconnect

        # Delete the item
        cmds.removeMultiInstance( parent.multiAttr( index ), b=True )

        return node, attrData

    def reorder_node( self, parent, nodes=None, startingIndex=0, keep=False, clean=False ):
        # We need to make all node to start at startingIndex and follow consecutively
        parent = mila_node( parent )

        # Get a list of all indices in the node to clean anything left empty
        origIndices = parent.indices()
        print "Original indices: %s" % origIndices

        if nodes is None:
            nodes = parent.children()
        else:
            nodes = [mila_node( node ) for node in nodes]

        node_id_data = []

        i = startingIndex
        for node in nodes:
            print "\t%r" % node
            p, index = node.parent()
            print "\t\t i:%s, index:%s" % ( i, index )
            if index != i:
                print "\t\tindexes don't match, disconnect the node and plug it to the correct place"
                node, data = self.get_node( p, index, keep=False )
                self.move_force( node, parent, index=i, nodeData=data, keep=keep )
            else:
                print "\t\tindexes match, don't move the node"

#             node_id_data.append( ( node, index, data ) )
            i += 1

#         for node, index, data in node_id_data:

        if clean and origIndices:
            # Clean all possible empty slot
            # we will range from the index 0, to the last possible index. It can be either the orginal last index; or the new last index
            self.clean( parent, range( max( i, origIndices[-1] ) + 1 ) )

        return i

    def move_force( self, source, dest, index=None, nodeData=None, keep=True ):
        # Remove the source from its parent and connect it to the index in the specified destination.
        # The connection will be forced. Anything connected to the destination will be discarded.
        # If nodeData is specified use it, else use the data from the node's parent

        source = mila_node( source )
        dest = mila_node( dest )

        print "Move_Force: %r %r at %s" % ( source, dest, index )

        parent, parent_id = source.parent()

        sourceData = None

        if parent and not nodeData:
            if keep:
                source, sourceData = self.get_node( parent, parent_id, keep=True )
            else:
                source, sourceData = self.get_node( parent, parent_id )
            nodeData = sourceData

        self.connect( source.outAttr(), dest.inAttr( index ) )
        if nodeData:
            self.set_node_data( dest, nodeData )

    def move( self, sources, destination, index, keep ):
        # Move all items to the specified index inside the destination
        # Everything will be reorganized so that each group node will have its first item at index 0 and everything stacked consecutively without hole

        print "####\nmove: %s, %s, %s, keep=%s" % ( sources, destination, index, keep )
#
#         print "INITIAL STATE"
#         print "destination children:"
#         print "%r" % destination
#         for node in destination.children():
#             print "\t%r" % node
#         print "Sources:"
#         for node in sources:
#             print "\t%r" % node
#             print "#####"

        pending_nodes = []
        parent_for_cleaning = set()

#         # If we specify keep=True, the source node won't be disconnected from their current position (e.i. instancing the node)
#         if keep:
#             print "keep"
#             # We don't remove the node from their original position
#             for node in sources:
#                 node_parent, parent_id = node.parent()
#                 if node_parent:
#                     pending_nodes.append( self.get_node( node_parent, parent_id ) )
#                 else:
#                     pending_nodes.append( ( node, {} ) )
#         else:
#             # First, remove all sources so we make some room for reodering
#             # Keep track of their foreign parent to clean them at the end
#             for node in sources:
#                 node_parent, parent_id = node.parent()
#                 if node_parent and parent_id is not None:
#                     if node_parent != destination:
#                         # We are taking a node from another group node, it will leave an empty plug in it, keep track of it for cleanning
#                         parent_for_cleaning.add( node_parent )
#                     pending_nodes.append( self.get_node( node_parent, parent_id, keep=False ) )
#                 else:
#                     pending_nodes.append( ( node, {} ) )

        # First get all sources so we make some room for reodering and cleaning
        # Keep track of their foreign parent to clean them at the end if nescesary
        for node in sources:
#             print "node: %s" % repr( node )
            node_parent, parent_id = node.parent()
#             print "node Parent: %r" % node_parent
#             print "parent_id: %s" % parent_id
            if node_parent and parent_id is not None:
#                 print "\t doing stuff with parent to get data"
                if not keep and node_parent != destination:
                    # We are taking a node from another group node, it will leave an empty plug in it, keep track of it for cleanning
                    parent_for_cleaning.add( node_parent )
                pending_nodes.append( self.get_node( node_parent, parent_id, keep=keep ) )
            else:
#                 print "\t doing nothing, only passing node to list: %r" % node
                # the node has no parent, so no data
                pending_nodes.append( ( node, {} ) )

#         print "pending_nodes:"
#         for item in pending_nodes:
#             print "\t %s" % repr( item )

        self.dgModifier.doIt()

#         print "#####\tAFTER DOIT for get pending nodes"
#         print "destination children:"
#         print "%r" % destination
#         for node in destination.children():
#             print "\t%r" % node
#         print "#####"
        # We are moving the source nodes to the specified index
        # Before we can do any work, we need to plan all moves to be as efficient as possible

        before_nodes = []
        after_nodes = []
#         print "Getting before and after nodes, for index: %s " % index

        # We will store a simple index, starting from zero.
        # If the beforeNodes indexes match our simple index, it mean it is in the right place and doens't need to be moved
        for child, child_id  in destination.children( index=True ):
#             print "\t child: %s" % repr( child )
            if child_id < index:
#                 print "\t\tputting to before node: %s" % repr( child )
                before_nodes.append( child )
            else:
#                 print "\t\tputting to after node: %s" % repr( child )
                after_nodes.append( self.get_node( destination, child_id, keep=False ) )

#         print "before_nodes:"
#         for item in before_nodes:
#             print "\t %s" % repr( item )

        if not keep and before_nodes and node.parent()[0]:
            # We are doing a move, if the node comes from the top of the layers we need to reorder all nodes before the destination index
            index = self.reorder_node( destination, before_nodes, 0 )
#         else:
#             # We don't remove any node, the stack on top of the destination cannot be dirty, we don't reorder
#             lastIndex = index
#         print "after_nodes:"
#         for item in after_nodes:
#             print "\t %s" % repr( item[0] )

        # Now put the sources right after the last node we reordered
#         i = lastIndex
        if pending_nodes:
            for node, data in pending_nodes:
                self.move_force( node, destination, index=index, nodeData=data )
                index += 1

        # Now add all after nodes after the last moved node
        for node, data in after_nodes:
            self.move_force( node, destination, index=index, nodeData=data )
            index += 1

#         print "doIt before cleaning so all nodes are already disconnected"
        self.dgModifier.doIt()

        # Our destination node might need a little clean up to remove trailing empty plugs
#         print "Clean destination"
        self.clean( destination )

        # Now clean all modified foreign group, they might have holes in their plugs
#         print "Clean previous parent of moved nodes":
        for node in parent_for_cleaning:
#             print "#####\n\tCleaning: %r" % node
            self.reorder_node( node, clean=True )
#             print "End Cleaning \n######"

    def hasSyntax( self, *args ):
        return True


def commandSyntax():

    syntax = OpenMaya.MSyntax()

    # -move
    try:
        syntax.addFlag( kMoveFlag, kMoveLongFlag )
    except Exception, e:
        sysPrint( e.str() )

    # -node "node_name"
    try:
        syntax.addFlag( kNodeFlag, kNodeFlagLong, OpenMaya.MSyntax.kString )
    except Exception, e:
        sysPrint( str( e ) )

    # -parent "node_name"
    try:
        syntax.addFlag( kParentFlag, kParentFlagLong, OpenMaya.MSyntax.kString )
    except Exception, e:
        sysPrint( str( e ) )

    # -source "node_name" [multi]
    try:
        syntax.addFlag( kSourceFlag, kSourceFlagLong, OpenMaya.MSyntax.kString )
        syntax.makeFlagMultiUse( kSourceFlag )
    except Exception, e:
        sysPrint( str( e ) )

    # -destination "node_name"
    try:
        syntax.addFlag( kDestinationFlag, kDestinationFlagLong, OpenMaya.MSyntax.kString )
    except Exception, e:
        sysPrint( str( e ) )

    # -index int
    try:
        syntax.addFlag( kIndexFlag, kIndexFlagLong, OpenMaya.MSyntax.kLong )
    except Exception, e:
        sysPrint( str( e ) )

    # -enable
    try:
        syntax.addFlag( kEnableNodeFlag, kEnableNodeFlagLong )
    except Exception, e:
        sysPrint( str( e ) )

    # -value int
    try:
        syntax.addFlag( kValueFlag, kValueFlagLong, OpenMaya.MSyntax.kLong )
    except Exception, e:
        sysPrint( str( e ) )

    # -solo
    try:
        syntax.addFlag( kSoloFlag, kSoloFlagLong )
    except Exception, e:
        sysPrint( str( e ) )

    # -removeSolo
    try:
        syntax.addFlag( kRemoveSoloFlag, kRemoveSoloFlag )
    except Exception, e:
        sysPrint( str( e ) )

    # -delete
    try:
        syntax.addFlag( kDeleteFlag, kDeleteFlagLong )
    except Exception, e:
        sysPrint( str( e ) )

    # -keep
    try:
        syntax.addFlag( kKeepFlag, kKeepFlagLong )
    except Exception, e:
        sysPrint( str( e ) )

    # -force
    try:
        syntax.addFlag( kForceFlag, kForceFlagLong )
    except Exception, e:
        sysPrint( str( e ) )

    return syntax


class milaDragAndDrop( OpenMayaMPx.MPxDragAndDropBehavior ):

    def __init__( self ):
        OpenMayaMPx.MPxDragAndDropBehavior.__init__( self )

    @staticmethod
    def creator():
        return OpenMayaMPx.asMPxPtr( milaDragAndDrop() )

    def shouldBeUsedFor( self, sourceNode, destinationNode, sourcePlug=None, destinationPlug=None ):
        # MObject, MObject, MPlug, MPlug

        dependNode = OpenMaya.MFnDependencyNode( destinationNode )
        sysPrint( "dest type: %s" % dependNode.typeName() )
        if dependNode.typeName() == "mila_layer" or dependNode.typeName() == "mila_mix" or dependNode.typeName() == "mila_material" and destinationPlug is not None:

            sysPrint( "dest plug: %s" % destinationPlug.partialName( 0, 0, 0, 0, 0, 1 ) )
            plugName = destinationPlug.partialName( 0, 0, 0, 0, 0, 1 ).split( "." )[-1]

            if plugName == "bump":
                # Test if the source has an outAlpha Attribute
                src = OpenMaya.MFnDependencyNode( sourceNode )
                # Get the outAlpha plug
                try:
                    outAlpha = src.findPlug( "outAlpha" )
                except RuntimeError, e:
                    sysPrint( e.str() )
                    sysPrint( "going into a mila_layer.bump but without outALpha, ignore" )
                    return False

                sysPrint( "going into a mila_layer.bump from node with outAlpha" )
                return True

        sysPrint( "ignore" )
        return False

    def connectNodeToAttr ( self, sourceNode, destinationPlug, force ):
        # MObject, MPlug, bool

        sysPrint( "testing source type" )
        bumpObj = None
        dg = OpenMaya.MDGModifier()
        if sourceNode.hasFn( OpenMaya.MFn.kTexture2d ):
            sysPrint( "source is a texture2D" )
            bumpObj = dg.createNode( "bump2d" )
        elif sourceNode.hasFn( OpenMaya.MFn.kTexture3d ):
            sysPrint( "source is a texture3D" )
            bumpObj = dg.createNode( "bump3d" )
        dg.doIt()

        src = OpenMaya.MFnDependencyNode( sourceNode )
        # Get the outAlpha plug (we don't need to check, it must exists)
        outAlpha = src.findPlug( "outAlpha", True )

        bump = OpenMaya.MFnDependencyNode( bumpObj )
        sysPrint( "bump; %s" % bump.name() )
        bumpValue = bump.findPlug( "bumpValue", True )
        outNormal = bump.findPlug( "outNormal", True )

        dg.connect( outAlpha, bumpValue )
        dg.connect( outNormal, destinationPlug )

        sysPrint( "destinationPlug: %s" % destinationPlug.name() )

        dg.doIt()


def initializePlugin( mobject ):
    mplugin = OpenMayaMPx.MFnPlugin( mobject, "", "", "Any" )

    try:
        mplugin.registerCommand( "milaMaterial", milaMaterial.creator, commandSyntax )
    except:
        sys.stderr.write( "Failed to register milaMaterial command" )
        raise

    try:
        mplugin.registerDragAndDropBehavior( "milaDragAndDrop", milaDragAndDrop.creator )
    except:
        sys.stderr.write( "Failed to register drag and drop: %s\n" % "milaDragAndDrop" )
        raise


def uninitializePlugin( mobject ):
    mplugin = OpenMayaMPx.MFnPlugin( mobject )

    try:
        mplugin.deregisterCommand( "milaMaterial" )
    except:
        sys.stderr.write( "Failed to deregister milaMaterial command" )
        raise

    try:
        mplugin.deregisterDragAndDropBehavior( "milaDragAndDrop" )
    except:
        sys.stderr.write( "Failed to deregister drag and drop: %s\n" % "milaDragAndDrop" )
        raise
