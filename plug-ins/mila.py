
import sys
import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx

from mila_node import *

import pprint

def sysPrint( truc ):
    sys.__stdout__.write( "%s\n" % truc )
    
    
kMoveFlag = "-m"
kMoveLongFlag = "-move"
kSourceFlag = "-s"
kSourceFlagLong = "-source"
kDestinationFlag = "-d"
kDestinationFlagLong = "-destination"
kIndexFlag = "-i"
kIndexFlagLong = "-index"
kKeepFlag = "-k"
kKeepFlagLong = "-keep"

kPlugDict = 0
kValueDict = 1

class Action():
    kNothing = -1
    kMove = 0
    kRemove = 1
    kClean = 2
    
    
class milaMaterial( OpenMayaMPx.MPxCommand ):
    
    def __init__(self):
        OpenMayaMPx.MPxCommand.__init__(self)
        
        self.sources = []
        self.destination = None
        
        self.destination_index = 0
        
        self.keep = False
        
        self.action = Action.kNothing
        
        self.dgModifier = OpenMaya.MDGModifier()
        self.sel = OpenMaya.MSelectionList()
        
    @staticmethod
    def creator():
        return OpenMayaMPx.asMPxPtr(milaMaterial())
    
    def doIt(self, argList):
        
        sysPrint("\n########")
        
        for i in range( argList.length() ):
            sysPrint( "argList: %s" % argList.asString(i) )
        
        try:
            argParser = OpenMaya.MArgParser( self.syntax(), argList)
        except Exception, e:
            sysPrint( "Error parsing syntax" )
            raise AttributeError( "Wrong argument call: %s" % str(e))
        
        if argParser.isFlagSet( kMoveFlag ):
            sysPrint( "We need to move !" )
            
            self.action = Action.kMove
            
            if not ( argParser.isFlagSet(kSourceFlag) and argParser.isFlagSet(kDestinationFlag)):
                sysPrint( "not enougth argument" )
                return;
            
            for i in range( argParser.numberOfFlagUses( kSourceFlag ) ):
                arg = argParser.flagArgumentString( kSourceFlag, i )
                node = mila_node( arg )
                if not node:
                    raise AttributeError( "%s is not a valid mila node" % arg )
                self.sources.append(node)
            
            dest_arg = argParser.flagArgumentString(kDestinationFlag, 0)
            index_arg = argParser.flagArgumentInt(kDestinationFlag, 1)
            
            self.destination = mila_node(dest_arg)
            self.destination_index = index_arg
            
            if not self.destination:
                raise AttributeError( "Source and/or destination is not a valid mila node." )
            
            self.keep = argParser.isFlagSet( kKeepFlag )
            
            
        else:
            sysPrint( "Nohting to do" )
            
            
        self.redoIt()
                     
    def redoIt(self, *args):
        
        if self.action == Action.kMove:
#             import pprint
#             node, data = self.get_node(self.destination, self.destination_index, self.keep)
#             print "Node: %s" % repr(node)
#             pprint.pprint(data)
            self.move()
            
        self.dgModifier.doIt()
        
        
        
    def undoIt(self, *args):
        
        self.dgModifier.undoIt()
        
    def isUndoable(self, *args):
        return True
        
    def _get_MPlug(self, source, destination=None ):
        
        # Create Empty Plugs
        sourcePlug = OpenMaya.MPlug()
        destPlug = OpenMaya.MPlug()
        
        # get element from input string
        self.sel.add( source ) 
        if destination:
            self.sel.add( destination )
        
        self.sel.getPlug( 0, sourcePlug )
        
        if destination:
            self.sel.getPlug( 1, destPlug )
        self.sel.clear()
        
        if destination:
            return sourcePlug, destPlug
        else:
            return sourcePlug
    
    def get_connection_or_value( attribute ):
        
        plug = self._get_MPlug( attribute )
        
        
        
            
        bool
        Mplug.asBool()
        
        float
        MPlug.asDouble()

        float3
        MPlug.child(0).asDouble()
        MPlug.child(1).asDouble()
        MPlug.child(2).asDouble()
        
        enum
        MPlug.asShort()
        
        
        plugs = OpenMaya.MPlugArray()
        plug.isConnected()

    
        connection = OpenMaya.MGlobal.executeCommandStringResult( "connectionInfo  -sourceFromDestination %s" % attribute )
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
    
        if isinstance( value, ( str, unicode ) ) and self.objExists( value ):
            try:
                self.connect( value, attr )
            except RuntimeError, e:
                if "Data types of source and destination are not compatible" in str( e ):
                    pass
                else:
                    raise
        else:
            attr_type = OpenMaya.MGlobal.executeCommandStringResult( "getAttr -type %s" % attr )
            try:
                if attr_type in ( 'double3', 'float3' ):  # value returned is a list of one tuple, ie [(r,g,b)]
                    self.setAttr( attr, *value, type=attr_type )
                elif attr_type == "string":
                    self.setAttr( attr, value, type=attr_type )
                else:
                    self.setAttr( attr, value )
            except RuntimeError, e:
                if "locked or connected" in str( e ):
                    pass
                else:
                    raise
    
    def removeMultiInstance(self, plugName ):
        
        cmd += representationsPlug[numElements-1].name();
        OpenMaya.MGlobal.executeCommand(cmd);
        
        
    def disconnect(self, source, destination ):
        
        print "disconnect: %s, %s" % ( repr(source), repr(destination))
        sourcePlug, destPlug = self._get_MPlug(source, destination) 
        self.dgModifier.disconnect( sourcePlug, destPlug )
        
    def connect(self, source, destination ):
        
        sourcePlug, destPlug = self._get_MPlug(source, destination) 
        self.dgModifier.connect( sourcePlug, destPlug )
        
    def objExists(self, input):
        
        sel = OpenMaya.MSelectionList()
        
        try:
            sel.add( input )  
        except RuntimeError, e:
            if "kInvalidParameter" in str(e):
                return False
        else:
            raise
        
        return True
        
        
    def set_node_data( self, node, data, index=0 ):
        
        if not data:
            return
        
        # Get a plug to the correct index parent plug
        
        multi_plug = self.get_multi_plug( node.obj )
        
        parentPlug = multi_plug.elementByLogicalIndex(index)
        plugDict = {}
        for i in range( parentPlug.numChildren() ):
            p = parentPlug.child(0)
            attributeName = OpenMaya.MFnAttribute( p.attribute() ).name()
            plugDict[attributeName] = p.name()
        
        import pprint
        pprint.pprint(plugDict)
        
        return
        
        # First set all Plug value
        for item in data[kValueDict]:
            print "Set Value %s : %s" % ( item[0], item[1])
#             self.dgModifier.newPlugValueDouble( item[0], item[1] )
        self.dgModifier.doIt()
        
        # Now Connect all plugs
        for item in data[kPlugDict]:
            print "Connect %s to %s" % ( item[0], item[1].name())
#             self.dgModifier.connect( item[0], item[1] )

#         if self.type() != "group" or not data:
#             return
#         
#         return
# 
#         
#         for attr in data:
#             if self.objExists( self.multiAttr( index ) + "." + attr ):
#                 set_connection_or_value( self.multiAttr( index ) + "." + attr, data[attr] )
        
    def clean( node, indices=None ):
        # Remove all empty entry in the node
    
        node = mila_node( node )
        if indices is None:
            indices = node.indices()
    
        for i in indices:
            if not node.child( i ):
                self.removeMultiInstance( node.multiAttr( i ) )

    def get_multi_plug(self, obj):
        
        fn = OpenMaya.MFnDependencyNode( obj )
        
        try:
            return fn.findPlug( "components" )
        except Exception, e:
            if "kInvalidParameter" in str(e):
                return fn.findPlug( "layers")
            else:
                raise
        
    def get_node( self,  parent=None, index=None, keep=False ):
        print "GetNode: %s at %s, keep:%s" % (repr(parent), index, keep)
    
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
        
        """ remove the node from the destination """
        parent = mila_node( parent )
        
        multiPlug = self.get_multi_plug( parent.obj )
        
        multiPlugIndex = multiPlug.elementByLogicalIndex(index)
        
        data = { kPlugDict:[], kValueDict: [] }
        
        # Get Data for all elements of the compound array plug
        for i in range( multiPlugIndex.numChildren() ):
            plug = multiPlugIndex.child(i)
            attribute = OpenMaya.MFnAttribute( plug.attribute() ).name()
            
            compoundPlugArray = OpenMaya.MPlugArray()
            compoundConnected = plug.connectedTo( compoundPlugArray, True, False)
            
            # First, check if we have a compound plug
            # We do not want to get the value of a compound plug, it has no meaning
            # we will get value/connection of all its child
            plugArray = OpenMaya.MPlugArray()
            if plug.isCompound():
                # Loop on all Child 
                for i in range( plug.numChildren() ):
                    childPlug = plug.child(i)
#                     childPlugName = childPlug.partialName( False, False, False, True, False, True)
                    childAttribute = OpenMaya.MFnAttribute( childPlug.attribute() ).name()
                    
                    if childPlug.connectedTo( plugArray, True, False ):
                        data[kPlugDict].append( (childAttribute, plugArray[0] ) )
                    else:
                        data[kValueDict].append( (childAttribute, getValue(childPlug) ) )
            elif not compoundConnected:
                # Input is not a compount 
                data[kValueDict].append( ( attribute, getValue(plug) ) )
                        
            # we still need to check for connection to the compound plug
            if compoundConnected:
                data[kPlugDict].append( ( attribute, compoundPlugArray[0] ) )
                
        node = parent.child( index )
        if node and not keep:
            self.disconnect( node.outAttr(), parent.inAttr(index))
        return node, data
    
    def reorder_node( self, parent, nodes=None, startingIndex=0, keep=False, clean=False ):
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
            node, data = self.get_node( p, index )
            node_id_data.append( ( node, index, data ) )
    
        i = startingIndex
        for node, index, data in node_id_data:
            if index != i:
                self.move_force( node, parent, index=i, nodeData=data, keep=keep )
            i += 1
    
        if clean and origIndices:
            # Clean all possible empty slot
            # we will range from the index 0, to the last possible index. It can be either the orginal last index; or the new last index
            self.clean( parent, range( max( i, origIndices[-1] ) + 1 ) )
    
        return i
    
    def move_force( self, source, dest, index=None, nodeData=None, keep=True ):
        # Remove the source from its parent and connect it to the index in the specified destination.
        # The connection will be forced. Anything connected to the destination will be discarded.
        # If nodeData is specified use it, else use the data from the node's parent
        import pprint
        
        pprint.pprint( nodeData)
        
        source = mila_node( source )
        dest = mila_node( dest )
        
        print "Move_Force: %s %s at %s" % (repr(source), repr(dest), index)
    
        parent, parent_id = source.parent()
        
        sourceData = None
    
        if parent and not nodeData:
            if keep:
                source, sourceData = self.get_node( parent, parent_id, keep=True )
            else:
                source, sourceData = self.get_node( parent, parent_id )
        else:
            sourceData = nodeData
            
        print "Connect Attr"
        pprint.pprint( sourceData )
    
        self.connect( source.outAttr(), dest.inAttr( index ) )
        if sourceData:
            print "set node data"
            self.set_node_data( dest, sourceData )
        
    def move( self ): 
        # Move all items to the specified index inside the destination
        # Everything will be reorganized so that each group node will have its first item at index 0 and everything stacked consecutively without hole
        
        sources = self.sources
        dest = self.destination
        index = self.destination_index
        keep = self.keep
        
        print "move: %s, %s, %s, keep=%s" % ( sources, dest, index, keep)
    
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
#                     if node_parent != dest:
#                         # We are taking a node from another group node, it will leave an empty plug in it, keep track of it for cleanning
#                         parent_for_cleaning.add( node_parent )
#                     pending_nodes.append( self.get_node( node_parent, parent_id, keep=False ) )
#                 else:
#                     pending_nodes.append( ( node, {} ) )
                    
        # First get all sources so we make some room for reodering and cleaning
        # Keep track of their foreign parent to clean them at the end if nescesary
        for node in sources:
            print "node: %s" % repr(node)
            node_parent, parent_id = node.parent()
            if node_parent and parent_id is not None:
                if not keep and node_parent != dest:
                    # We are taking a node from another group node, it will leave an empty plug in it, keep track of it for cleanning
                    parent_for_cleaning.add( node_parent )
                pending_nodes.append( self.get_node( node_parent, parent_id, keep=keep ) )
            else:
                # the node has no parent, so no data
                pending_nodes.append( ( node, {} ) )
    
        print "pending_nodes:"
        for node in pending_nodes:
            print "\t %s" % epr(node)
        
        # We are moving the source nodes to the specified index
        # Before we can do any work, we need to plan all moves to be as efficient as possible
    
        before_nodes = []
        after_nodes = []
        print "Getting before and after nodes, for index: %s " % index
        for child, child_id  in dest.children( index=True ):
            print "\t child_id: %s" % child_id
            if child_id < index:
                print "\tputting to before node: %s" % repr(child)
#                 before_nodes.append( child )
                before_nodes.append( self.get_node( dest, child_id, keep=False) )
            else:
                print "\tputting to after node: %s" % repr(child)
                after_nodes.append( self.get_node( dest, child_id, keep=False) )
    
        if not keep and before_nodes and node.parent()[0]:
            # We are doing a move, if the node comes from the top of the layers we need to reorder all nodes before the dest index
            lastIndex = self.reorder_node( dest, before_nodes, 0 )
        else:
            # We don't remove any node, the stack on top of the destination cannot be dirty, we don't reorder
            lastIndex = index

        print "before_nodes:"
        for node in before_nodes:
            print "\t %s" % epr(node)
        print "after_nodes:"
        for node in after_nodes:
            print "\t %s" % epr(node)
    
        # Now put the sources in the gap created earlier
        i = 0; #lastIndex
        if pending_nodes:
            for node, data in pending_nodes:
                self.move_force( node, dest, index=i, nodeData=data )
                i += 1
#             lastIndex = i
    
        # Now add all after nodes
#         for node, data in after_nodes:
#             self.move_force( node, dest, index=i, nodeData=data )
#             i += 1
#     
#         # Now clean all modified foreign group
#         for node in parent_for_cleaning:
#             self.reorder_node( node, clean=True )
            
    
    def hasSyntax(self, *args):
        return True
    
def commandSyntax():
    
    syntax = OpenMaya.MSyntax()
    
    try:
        syntax.addFlag( kMoveFlag, kMoveLongFlag)
    except Exception, e:
        sysPrint(e.str())
        
    try:
        syntax.addFlag( kSourceFlag, kSourceFlagLong, OpenMaya.MSyntax.kString )
        syntax.makeFlagMultiUse( kSourceFlag )
    except Exception, e:
        sysPrint(str(e))
    
    try:
        syntax.addFlag( kDestinationFlag, kDestinationFlagLong,  OpenMaya.MSyntax.kString, OpenMaya.MSyntax.kLong)
    except Exception, e:
        sysPrint(str(e))
        
    try:
        syntax.addFlag( kKeepFlag, kKeepFlagLong )
    except Exception, e:
        sysPrint( str(e) )
    
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
        if sourceNode.hasFn(OpenMaya.MFn.kTexture2d):
            sysPrint( "source is a texture2D" )
            bumpObj = dg.createNode( "bump2d" )
        elif sourceNode.hasFn(OpenMaya.MFn.kTexture3d):
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
        mplugin.deregisterCommand("milaMaterial")
    except:
        sys.stderr.write( "Failed to deregister milaMaterial command" )
        raise

    try:
        mplugin.deregisterDragAndDropBehavior( "milaDragAndDrop" )
    except:
        sys.stderr.write( "Failed to deregister drag and drop: %s\n" % "milaDragAndDrop" )
        raise
