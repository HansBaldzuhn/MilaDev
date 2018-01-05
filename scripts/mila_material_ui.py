# -*- coding: utf-8 -*-

# Python
import os
from shiboken import wrapInstance, isValid
import copy

# Qt
from PySide import QtGui, QtCore

# Maya modules
import maya.cmds as cmds
import maya.OpenMayaUI as OpenMayaUI
import maya.OpenMaya as OpenMaya

# Mila modules
from mila_layout_template import AE_mila_base_ui
from mila_node import *

# Load mila plugin for drag and drop behavior
cmds.loadPlugin( "mila", quiet=True )


# Enum Classes
class MoveDirection():
    kNone = None
    kDown = 1
    kUp = -1

class Position():
    kDefault = -1
    kAbove = 0
    kUnder = 1
    kInside = 2
    kLast = 3

class MoveBehaviour():
    kMove = 0
    kCopy = 1
    kLink = 2

class Selection():
    kToggle = 1
    kAdd = 2
    kRemove = 3
    kClear = 4
    kReplace = 5


class DisabledUndo( object ):

    def __enter__( self ):
        cmds.undoInfo( stateWithoutFlush=False )

    def __exit__( self, *args ):
        cmds.undoInfo( stateWithoutFlush=True )

class UndoChunk( object ):

    def __init__( self, name="milaUndoChunk" ):
        self.name = name

    def __enter__( self ):
        cmds.undoInfo( openChunk=True, chunkName=self.name )

    def __exit__( self, *args ):
        cmds.undoInfo( closeChunk=True )
# 
# class IprWait( object ):
# 
#     def __init__( self, node ):
# 
#         self.node = node
# 
#     def __enter__( self ):
# #         cmds.Mayatomr(pauseTuning=True)
#         pass
# 
#     def __exit__( self, *args ):
# #         cmds.Mayatomr(pauseTuning=False)
#         pass
#         # Now do a fake edit to force the ipr to refresh


def ICON( imageFile ):

    for path in os.getenv( "XBMLANGPATH" ).split( os.pathsep ):
        if path.endswith( '%B' ):
            path = path[:-2]
        fullPath = os.path.join( path, imageFile )
        if os.path.isfile( fullPath ):
            return fullPath

    return ""

def STR_POS( pos ):

    if pos == 0:
        return "kAbove"
    elif pos == 1:
        return "kUnder"
    elif pos == 2:
        return "kInside"
    elif pos == 3:
        return "kLast"

def POS_STR( pos ):

    if pos is None:
        return "kNone"
    elif pos == 1:
        return "kDown"
    elif pos == -1:
        return "kUp"

def STR_BEHAV( pos ):

    if pos is 0:
        return "kMove"
    elif pos == 1:
        return "kCopy"
    elif pos == 2:
        return "kLink"

AE_MILA_UI = {}



class MilaTreeLayout( QtGui.QWidget ):

    def __init__( self, input_, parent=None ):
        super( MilaTreeLayout, self ).__init__( parent )

        # Component UI attributes
        self.componentUI = None
        
        set_widget_name( self, "milaTree" )

        self.layout = QtGui.QVBoxLayout( self )
        self.layout.setContentsMargins( 0, 0, 0, 0 )
        self.layout.setSpacing( 0 )

        set_layout_name( self.layout, "milaTreeLayout" )


        self.reloadButton = QtGui.QPushButton( "Reload", self )

        self.treeCreationLayout = QtGui.QVBoxLayout()

        # Tree/Create Layout
        self.treeCreateLayout = QtGui.QHBoxLayout()
        self.treeCreateLayout.setContentsMargins( 0, 0, 0, 0 )
        self.treeCreateLayout.setSpacing( 0 )

        # Create Component
        self.createComponentParentLayout = QtGui.QVBoxLayout()
        self.createComponentParentLayout.setContentsMargins( 0, 0, 0, 0 )
        self.createComponentParentLayout.setSpacing( 0 )

        self.createComponentLayout = QtGui.QGridLayout()
        self.createComponentLayout.setContentsMargins( 0, 0, 0, 0 )
        self.createComponentLayout.setSpacing( 0 )

        # Tree UI
        self.treeUI = TreeWidget( input_, self )
        self.treeUI.updateComponentUI.connect( self.setComponent )
        self.treeUI.clearComponentUI.connect( self.clearComponent )

        self.resizeHandle = ResizeHandle( self )
        self.resizeHandle.resize.connect( self.treeUI.resize )

        column = 0
        row = 0

        for item in list( MILA_GROUP_TYPES ) + MILA_COMPONENT_TYPES:
            b = ComponentCreatorButton( item, self )
            b.clicked.connect( self.treeUI.addItem_clicked )
            self.createComponentLayout.addWidget( b, row, column )
            if column:
                row += 1
            column = not column

        self.parentLayout = parent

        self.reloadButton.clicked.connect( self.treeUI.reload )

        self.layout.addWidget( self.reloadButton )

        self.layout.addLayout( self.treeCreationLayout )

        self.createComponentParentLayout.addLayout( self.createComponentLayout )
        self.createComponentParentLayout.addStretch( 1 )

        self.treeCreateLayout.addLayout( self.createComponentParentLayout )
        self.treeCreateLayout.addWidget( self.treeUI )

        self.treeCreationLayout.addLayout( self.treeCreateLayout )
        self.treeCreationLayout.addWidget( self.resizeHandle )

        # Component layout, it will hold the AETemplate of the currently selected node
        self.componentLayout = QtGui.QVBoxLayout( self )
        self.componentLayout.setContentsMargins( 0, 0, 0, 0 )
        self.componentLayout.setSpacing( 0 )
        self.componentLayout.setSizeConstraint( QtGui.QLayout.SetNoConstraint )
        self.componentLayout.setEnabled( False )

        set_layout_name( self.componentLayout, "mila_component_layout" )
        self.layout.addLayout( self.componentLayout )

        self.layout.addStretch()

    def fullName( self ):
        ptr = OpenMayaUI.MQtUtil.findControl( self.objectName() )
        return OpenMayaUI.MQtUtil.fullName( long( ptr ) )

    def milaComponentLayout( self ):
        
        def AE_layout( tree ):
            
            ui = "|".join( tree.split( "|" )[:-2] )

            child = ""

            i = 0

            childOrder = [2, 0, 0, 0]

            for index in childOrder:

                child = cmds.layout( ui, query=True, childArray=True )
                if child:
                    child = child[index]
                else:
                    break
                ui += "|%s" % child
                
                i += 1
                if i > 50:
                    break
            return ui

        try:
            maya_comp_ui = AE_layout( self.fullName() )
        except RuntimeError:
            maya_comp_ui = None
            

        if maya_comp_ui and cmds.columnLayout( maya_comp_ui, query=True, exists=True ):
            # it's a valid maya ui, use it !
            return maya_comp_ui

        # Unable to find the Attribute Editor layout, use our own Qt layout
        self.componentLayout.setEnabled( True )
        maya_short_name = self.componentLayout.layout().objectName()
        maya_full_path = cmds.layout( maya_short_name, query=True, fullPathName=True )

        return maya_full_path



    @QtCore.Slot()
    def clearComponent( self ):
        if self.componentUI:
            self.componentUI.hide()


    @QtCore.Slot( MilaNode )
    def setComponent( self, node ):

        with UndoChunk( "setComponent( %s )" % node.name() ):
            if not self.componentUI:
                cmds.setParent( self.milaComponentLayout() )
                self.componentUI = AE_mila_base_ui()
                cmds.setParent( ".." )

            node_parent, index = node.parent()

            self.componentUI.setParentNode( node_parent.multiAttr( index=index ) )

            if node.type() != "group":
                self.componentUI.setNode( node.name() )
            else:
                self.componentUI.hideNode()


class ResizeHandle( QtGui.QFrame ):

    resize = QtCore.Signal( int )

    def __init__( self, parent ):
        super( ResizeHandle, self ).__init__( parent )

        self.setFrameStyle( QtGui.QFrame.HLine | QtGui.QFrame.Raised )
        self.setFixedHeight( 10 )

        self.setMouseTracking( True )

        self.startPosition = QtCore.QPoint()

    def mousePressEvent( self, event ):
        event.accept()

        if event.buttons() == QtCore.Qt.LeftButton:
            self.startPosition = event.pos()

    def mouseMoveEvent( self, event ):
        self.setCursor( QtCore.Qt.SplitVCursor )
        event.accept()

        if event.buttons() == QtCore.Qt.LeftButton:
            # Compute distance difference
            dist = event.pos() - self.startPosition
            self.resize.emit( dist.y() )



class TreeWidget( QtGui.QScrollArea ):

    updateComponentUI = QtCore.Signal( MilaNode )
    clearComponentUI = QtCore.Signal()

    def __repr__( self ):

        return 'TreeWidget("%s")' % self.node().name()

    def __init__( self, input_, parent ):
        super( TreeWidget, self ).__init__( parent )

        self.mainWidget = QtGui.QWidget( self )

        self.setFixedHeight( 200 )
        self.minValue = 80
        self.setWidgetResizable( True )

        self._node = None
        self._mila_node = None
        self._last_selected = None
        self.save_select = {}
        self._iconStateQuery = False
        
        self._menuItemList = ( "Select", "Copy", "Delete" )

        self.setAcceptDrops( True )

        self.setFrameStyle( QtGui.QFrame.StyledPanel | QtGui.QFrame.Sunken )

        pal = QtGui.QPalette()
        pal.setColor( QtGui.QPalette.Background, pal.base().color() )
        self.setPalette( pal )
        self.setAutoFillBackground( True )
        
        # Shortcuts
        self.copyShortcut = QtGui.QShortcut(QtGui.QKeySequence( "Ctrl+c"), self)
        self.copyShortcut.setAutoRepeat(False)
        self.copyShortcut.activated.connect( self.copySelectionToClipBoard )
        
        self.cutShortcut = QtGui.QShortcut(QtGui.QKeySequence( "Ctrl+x"), self)
        self.cutShortcut.setAutoRepeat(False)
        self.cutShortcut.activated.connect( self.cutSelectionToClipboard )
        
        self.pasteShortcut = QtGui.QShortcut(QtGui.QKeySequence( "Ctrl+v"), self)
        self.pasteShortcut.setAutoRepeat(False)
        self.pasteShortcut.activated.connect( self.pasteClipboard )
        
        self.duplicateShortcut = QtGui.QShortcut(QtGui.QKeySequence( "Ctrl+d"), self)
        self.duplicateShortcut.setAutoRepeat(False)
        self.duplicateShortcut.activated.connect( self.duplicate )

        # Drop Overlay Widget
        self.drop_overlay_widget = QtGui.QFrame( self )
        self.drop_overlay_widget.setFrameStyle( QtGui.QFrame.Box | QtGui.QFrame.Plain )
        self.drop_overlay_widget.setLineWidth( 3 )
        pal = QtGui.QPalette()
        pal.setColor( QtGui.QPalette.WindowText, pal.highlight().color() )
        self.drop_overlay_widget.setPalette( pal )
        self.drop_overlay_widget.hide()

        # We need a layout over our child_layout to keep a stretch at the bottom of the QFrame
        placeHolderLayout = QtGui.QVBoxLayout( self.mainWidget )
        placeHolderLayout.setContentsMargins( 0, 0, 0, 0 )
        placeHolderLayout.setSpacing( 0 )

        self.child_layout = QtGui.QVBoxLayout()
        self.child_layout.setContentsMargins( 0, 0, 0, 0 )
        self.child_layout.setSpacing( 0 )

        placeHolderLayout.addLayout( self.child_layout )
        placeHolderLayout.addStretch( 1 )
        placeHolderLayout.addSpacing( 8 )


        self.setWidget( self.mainWidget )

        self.setMila( input_ )

        set_widget_name( self, "milaTreeScroll" )

    @QtCore.Slot( int )
    def resize( self, difValue ):

        newHeight = self.height() + difValue

        if newHeight <= self.minValue:
            newHeight = self.minValue

        self.setFixedHeight( newHeight )

    @QtCore.Slot()
    def reload( self ):
        """ Clear and re feed the ui """

#        self.saveSelection()
#         self._node = mila_node( cmds.milaMaterial( initialize=self._mila_node.name() ))

#         with DisabledUndo():

        self.clear()
        self.feedUIRecurse()

        # Restore soloState
        solo_item = self.mila().soloItem()
        if solo_item:
            for item in self.children():
                if item.node() == solo_item:
                    item.setSolo()

        self.restoreSelection()

    def setMila( self, mila ):
        """ Set the ui to work on the specified node, it will also init the mila_material if nescessary.
        This function also peform a reload of the ui. """
        self._mila_node = mila_node( mila )
        self.reload()

#     def initializeMila( self ):
#         """ Set the ui to work on the specified node, it will also init the mila_material if nescessary.
#         This function also peform a reload of the ui. """

    def mila( self ):
        return self._mila_node
    
    def node( self ):
        """ 
        This function returns the hidden mila_layer node, it is nescessary to be able to treat the root (self) as a TreeItemWidget
        If there is something in the "save_layer" attr, the mila is currently in solo state.
        We need to consider this one instead of the layer in the "shader" attribute
        """
        # Initialise mila material, e.i. create a mila_layer
        self._node = cmds.milaMaterial( initialize=self.mila().name() )
    
        if cmds.connectionInfo( self.mila().shaderSaveAttr(), isExactDestination=True ):
            return self.mila().source( self.mila().shaderSaveAttr() )
        else:
            return self.mila().source( self.mila().inAttr() )

    def isRoot( self ):
        return True

    def root( self ):
        return self

    def type( self ):
        return self.node().type()

    def nodeType( self ):
        return self.node().nodeType()

    def parent( self ):
        return None

    def children( self ):
        return self.findChildren( TreeItemWidget )


    @QtCore.Slot( str )
    def addItem_clicked( self, type ):
        destination = self._last_selected
        with UndoChunk("addItem( %s, %s)" % (type, destination)):
            self.addItems( type, destination )


    def addItems( self, items, destination=None, position=Position.kDefault, uiOnly=False, behaviour=MoveBehaviour.kLink ):
        """ add a new Node to the tree, a MilaNode, the name of a mila_component or mila_layer or a mila type.
        The correct data will be build """

        if destination is None:
            destination = self
            
        if position == Position.kDefault:
            if destination.type() == "component":
                position = Position.kAbove
            else:
                position = Position.kInside
            

        if not isinstance( items, ( list, tuple ) ):
            items = [items]

        items = [ mila_node( item, create=True ) for item in items]

        keep = True

        # First try to delete all existing TreeItemWidget with the same nodes
        # Only if we are moving the nodes
        if not uiOnly and behaviour == MoveBehaviour.kMove:
            keep = False
            for treeItem in self.children():
                if treeItem.node() in items:
                    treeItem.setParent( None )
                    treeItem.deleteLater()

        elif behaviour == MoveBehaviour.kCopy:
            copy_items = []
            for item in items:
                copy_items.append( mila_copy( item ) )
            items = copy_items

        elif behaviour == MoveBehaviour.kLink:
            keep = True


        new_items = [TreeItemWidget( item, self ) for item in items]

        if uiOnly:
            # When we build the ui on existing graph, we only want to add the TreeWidgetItems without actualy adding any node
            for item in new_items:
                item.setParent( destination )
                destination.child_layout.addWidget( item )

                item.setState()

                try:
                    destination.expand()
                except AttributeError:
                    pass

        else:
            # Add all items to the tree
            
            parent, index = self.getIndex( destination, position )

            # Move the ui
            self.moveItem( new_items, parent, index=index )

            # Move the nodes
            cmds.milaMaterial( move=True,source=items, destination=parent.node().name(), index=index, keep=keep )

            # We need to refresh the state of the control since it may have changed after the move
            for item in new_items:
                item.setState()
                self.feedUIRecurse( item )

        return new_items

    def itemFromNode( self, node ):

        node = mila_node( node )
        if node:
            for child in self.children():
                if child.node() == node:
                    return child

    def resetSolo( self, _input, state=False ):

        for item in self.children():
            if not state or item.node() != _input.node():
                item.setSolo( False )
            elif state:
                item.setSolo( True )

    def removeItem( self, _input, delete_node=True ):

        # Test that the _input might not exists
        if not _input:
            return

        # Clear last selected if its the node we are deleting
        if self._last_selected == _input:
            self._last_selected = None

        node = _input.getNode()

        _input.setParent( None )
        _input.deleteLater()

        if delete_node:
            cmds.milaMaterial( delete=True, node=node.name() )
#             with UndoChunk( "mila_delete(%s)" % node.name() ):
#                 mila_delete( node )

        self.updateParentComponent()


    def updateParentComponent( self ):

        if self._last_selected:
            self.updateComponentUI.emit( self._last_selected.getNode() )

        else:
            self.clearComponentUI.emit()

    def feedUIRecurse( self, uiItems=None ):

        if not uiItems:
            uiItems = [self]

        if not isinstance( uiItems, ( list, tuple ) ):
            uiItems = [uiItems]

        with UndoChunk("feedUIRecurse( %s )" % uiItems):
            for uiItem in uiItems:
    
                uiItem.clear()
    
                for child in uiItem.node().children():
                    new_items = self.addItems( child, destination=uiItem, uiOnly=True )
                    for item in new_items:
                        self.feedUIRecurse( item )

    def getIndex( self, destination, position ):

        # We initialize the drop index to zero (default behaviour, putting the node in top of the layer)
        index = 0

        parent = destination
        
        if position <= Position.kUnder: # if pos is kUnder or kAbove
            # Droping above or under something, get its parent !")

            parent = destination.parent()

            # Get the index of the destination's parent
            index = parent.child_layout.indexOf( destination )


        if position == Position.kLast:
            # Droping on last!")
            # Get the index of the last item in the destination
            index = destination.child_layout.count()

        # If we need to put the new node under the destination increment the index (higher number is under)
        elif position == Position.kUnder:
            # Droping Under, add 1 to the index")
            # Position is kUnder, increment index
            index += 1
            
        return parent, index


    def moveItem( self, sources, parent, index=0 ):

        # Build all move command while moving the widgets and execute it later
        # So the ui update won't be delayed by the maya graph manipulation

        for item in sources:

            item.setParent( parent )
            parent.child_layout.insertWidget( index, item )
            index += 1


            # Always try to expand the item when droping on a node (it will do nothing for non-group items)
            self.feedUIRecurse( item )
            item.expand()
            try:
                parent.expand()
            except AttributeError:
                pass


    def clear( self ):
        """ Reset the TreeWidget, it will only perform a UI reset, the maya graph won't be affected """

        # Delete Qt layout"
        child = self.child_layout.takeAt( 0 )
        while child:
            widget = child.widget()
            if widget:
                widget.setParent( None )
                widget.deleteLater()
                del widget

            child = self.child_layout.takeAt( 0 )

        # Clear all private members
        self._last_selected = None

        # Emitting Clear Signal
        # It will tell the MilaTreeLayout to clear the component UI (where the attribute of the node might be displayed, right under the TreeWidget)
        self.clearComponentUI.emit()

    def saveSelection( self ):

        if not self.lastSelected():
            try:
                del self.save_select[self.mila().name()]
            except KeyError:
                pass
            return

        self.save_select[self.mila().name()] = self.lastSelected().getNode()

    def restoreSelection( self ):

        try:
            last_selected_node = self.save_select[self.mila().name()]
        except KeyError:
            return

        last_selected_item = self.itemFromNode( last_selected_node )
        self.select( last_selected_item )


    def select( self, itemList=None, mode=None, fast=False ):
        """ Select items in the TreeWidget
        This procedure is called by the clickEvent """

        if not itemList and mode != Selection.kClear:
            return

        # Allow the user to input a single argument instead of a list
        if not isinstance( itemList, ( tuple, list, set ) ):
            itemList = [itemList]

        # default behaviour for unspecified mode
        if mode is None:
            mode = Selection.kReplace

        if mode >= Selection.kClear:

            self._last_selected = None

            # Deselect every one
            for child in self.children():
                child.select( False )

            if mode == Selection.kReplace:
                for item in itemList:
                    item.select( True )
                    self._last_selected = item

        elif mode == Selection.kAdd:
            for item in itemList:
                item.select( True )
                self._last_selected = item

        elif mode == Selection.kRemove:
            for item in itemList:
                item.select( False )

        elif mode == Selection.kToggle:

            for item in itemList:
                state = not item.selected()

                item.select( state )

                if state:
                    self._last_selected = item

        # Show a color int on all occurence of the last selectedNode
        if self._last_selected:
            for item in self.children():
                if item.node() == self._last_selected.node():
                    item.setSelectHint( True )
                else:
                    item.setSelectHint( False )



        # Tell the MilaTreeLayout to update the component UI
        if not fast:
            self.updateParentComponent()
            self.saveSelection()

    def flattenItemList( self, itemList ):
        """
        Given a list of treeItemWidget, return only the top level items (ignore any child if their parent is in the list)
        """
        new_set = set( itemList )

        for item in itemList:

            new_set -= set( item.children() )

        return sorted( new_set, key=lambda x: self.itemTitleGeometry( x ).y() )

    def flattenedSelection( self ):
        """
        Return a list of item selected with only top level item
        """
        return self.flattenItemList( self.selected( sort=False ) )


    def selected( self, sort=True ):
        """ Return a list of all selected item in the tree. If the sorted flag is true, the items will be sorted from top to bottom """

        selection = []

        for item in self.children():
            if item.selected():
                selection.append( item )

        if sort:
            return sorted( selection, key=lambda x: self.itemTitleGeometry( x ).y() )
        else:
            return selection

    def lastSelected( self ):
        """ Return le last selected item """
        return self._last_selected

    def itemAt( self, pos, item_type=None ):

        if item_type is None:
            item_type = TreeItemWidget


        def findTreeItemWidget( input_ ):

            while not isinstance( input_, item_type ) and input_:
                input_ = input_.parent()
                if isinstance( input_, TreeWidget ):
                    # We should not reach this, if we do we might be between two ItemWidget
                    return input_

            return input_

        item = self.childAt( pos )

        if not item:
            # There is no widget under the mouse, return the top level widget ( TreeWidget )
            return self

        item = findTreeItemWidget( item )
        while not item:
            # Offset the position one pixel above until we find the right type of item
            pos += QtCore.QPoint( 0, -1 )

            item = self.childAt( pos )
            item = findTreeItemWidget( item )
        
        if not isinstance( item, item_type ):
            if isinstance( item, TreeWidget):
                return self
            return None

        return item

    def mouseDoubleClickEvent( self, event ):

        if event.buttons() == QtCore.Qt.LeftButton:

            item = self.itemAt( event.pos() )

            if not item or item is self:
                return

            item.showChildLayout( item.collapsed() )


    def mousePressEvent( self, event ):
        
        if QtGui.QApplication.keyboardModifiers() == QtCore.Qt.AltModifier:
            return
        
        if event.buttons() == QtCore.Qt.RightButton:
            event.accept()
            
            item = self.itemAt( event.pos() )
            
            popupMenu = AutoHideMenu( self )
            
            # Select
            action = QtGui.QAction( "Select Node", self ) 
            # item is a TreeItemWidget
            action.triggered.connect( item.node().select )
            popupMenu.addAction( action )
            
            popupMenu.popup( self.mapToGlobal( event.pos() ) )
                             
        if event.buttons() == QtCore.Qt.LeftButton:
            item = self.itemAt( event.pos() )
            
            mode = Selection.kReplace

            if not item or item.isRoot() or not self.itemClickableGeometry( item ).contains( event.pos() ):
                mode = Selection.kClear
                item = None
            else:
                if QtGui.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier:
                    # Add all item between the self._last_selectd and the clicked one
                    if self._last_selected:
                        sourceCenter = self.itemTitleGeometry( self._last_selected ).center()
                        destCenter = self.itemTitleGeometry( item ).center()

                        if sourceCenter.y() < destCenter.y():
                            tmp = sourceCenter
                            sourceCenter = destCenter
                            destCenter = tmp

                        mode = Selection.kAdd

                        for child in self.children():
                            if sourceCenter.y() >= self.itemTitleGeometry( child ).center().y() >= destCenter.y():
                                self.select( child, mode, fast=True )


                elif QtGui.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier:

                    mode = Selection.kToggle

            self.select( item, mode )
        
        elif event.buttons() == QtCore.Qt.MiddleButton:
            # We will most possibly start a drag and drop, we shoud not override the current selection
            item = self.itemAt( event.pos() )
            self.select( item, Selection.kAdd )
            
            pass
        
    def mouseMoveEvent( self, event ):

        item = self.itemAt( event.pos() )

        if item is self:
            event.ignore()
            return

        if not self.itemClickableGeometry(item).contains( event.pos() ):

            # Test if we are over a iconButton
            if self.itemButtonGeometry(item).contains( event.pos() ):
                button = self.itemAt( event.pos(), item_type=IconButton)
                
                if button:
                    if self._iconStateQuery is None:
                        # The state is not set, we are the first one, store the value
                        self._iconStateQuery = button.state()
                        
                    # Set the button state and the mila state manually, we can't trigger the signal because the drag will constantly call it
                    button.setState( self._iconStateQuery )
                    item.setState( self._iconStateQuery, set=True )
                return

            event.ignore()
            return

        event.accept()

        items = self.selected()
        
        if not items:
            return

        if event.buttons() == QtCore.Qt.LeftButton:
            # The user is doing a drag to drop somewere else

#             The user is drag-selecting
#             mode = Selection.kAdd
#             if QtGui.QApplication.keyboardModifiers() == QtCore.Qt.AltModifier:
#                 mode = Selection.kRemove
# 
#             self.select( item, mode, fast=True )
# 
#         elif QtGui.QApplication.mouseButtons() == QtCore.Qt.LeftButton: # or QtGui.QApplication.mouseButtons() == QtCore.Qt.RightButton:

#            if not item.selected():
#                self.select( item, Selection.kReplace )

            items = self.flattenedSelection()
            
            dragData = self._buildSelectionData(items)

            mimeData = QtCore.QMimeData()
            mimeData.setText( dragData )

            drag = QtGui.QDrag( self )
            drag.setMimeData( mimeData )
            drag.setPixmap( self._buildDragPixmap( items ) )

            # If we are moving, delete the original nodes
            if drag.start( QtCore.Qt.MoveAction | QtCore.Qt.CopyAction | QtCore.Qt.LinkAction ) == QtCore.Qt.MoveAction:
                for item in items:
                    self.removeItem( item, delete_node=False )
                    
    def mouseReleaseEvent(self, event):
        # reset the iconStateQuery
        self._iconStateQuery = None

    def _getDragData( self, event ):

        data = event.mimeData()

        if data.hasText():
            dragData = []
            for item in data.text().split():
                data = item.split( "," )
                if len( data ) == 3:
                    dragData.append( mila_node( data[0], data[1], data[2] ) )
                else:
                    dragData.append( mila_node( data[0] ) )
            return dragData
        else:
            return None

    def dragLeaveEvent( self, event ):
        event.accept()
        self._resetDropIndicator()

    def dragEnterEvent( self, event ):

        # Test drag input
        drag_nodes = self._getDragData( event )

        if not drag_nodes:
            event.ignore()
            self._resetDropIndicator()
            event.ignore()
            return

        for node in drag_nodes:
            if not node:
                # We are draging a non mila node, ignore
                event.ignore()
                self._resetDropIndicator()
                return

        event.accept()

        return

    def dragMoveEvent( self, event ):

        drag_nodes = self._getDragData( event )

        position, drop_item = self._getDropPosition( event.pos() )
        
        if drop_item is not self:
            drop_node = drop_item.getNode()

            if not drop_item:
                event.ignore()
                self._resetDropIndicator()
                return

            if drop_node in drag_nodes:
                event.ignore()
                self._resetDropIndicator()
                return

            else:
                for node in drag_nodes:
                    if drop_node in node.children( recurse=True ):
                        event.ignore()
                        self._resetDropIndicator()
                        return

        event.accept()

        self._resetDropIndicator()
        self._drawDropIndicator( self._getDropPosition( event.pos() ) )


    def dropEvent( self, event ):

        self._resetDropIndicator()
        

        position, drop_item = self._getDropPosition( event.pos() )

        drag_nodes = self._getDragData( event )

        behaviour = MoveBehaviour.kLink
        if QtGui.QApplication.keyboardModifiers() == QtCore.Qt.AltModifier:
            # Instance the node
            event.setDropAction( QtCore.Qt.LinkAction )
            behaviour = MoveBehaviour.kLink
        elif QtGui.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier:
            # Copy the node
            event.setDropAction( QtCore.Qt.CopyAction )
            behaviour = MoveBehaviour.kCopy
        else:
            # move the node
            event.setDropAction( QtCore.Qt.MoveAction )
            behaviour = MoveBehaviour.kMove
        event.accept()
        
        with UndoChunk("addItems %s, %s, %s, %s" % (drag_nodes, drop_item, position, STR_BEHAV(behaviour))):
            self.addItems( drag_nodes, drop_item, position, behaviour=behaviour )


    def selfGeometry( self ):
        geo = self.geometry()
        return QtCore.QRect( 0, 0, geo.width(), geo.height() )

    def itemTitleGeometry( self, item ):
        try:
            return item.titleGeometry().translated( item.mapTo( self, item.titleGeometry().topLeft() ) )
        except AttributeError:
            return QtCore.QRect()

    def itemGeometry( self, item ):
        try:
            return item.selfGeometry().translated( item.mapTo( self, item.selfGeometry().topLeft() ) )
        except AttributeError:
            return QtCore.QRect()

    def itemClickableGeometry( self, item ):
        try:
            return item.clickableGeometry().translated( item.mapTo( self, item.titleGeometry().topLeft() ) )
        except AttributeError:
            return QtCore.QRect()

    def itemButtonGeometry( self, item ):
        try:
            return item.buttonGeometry().translated( item.mapTo( self, item.titleGeometry().topLeft() ) )
        except AttributeError:
            return QtCore.QRect()

    # Drag and Drop utility ---

    def _getDropPosition( self, pos ):

        drop_item = self.itemAt( pos )
        
        if not drop_item:
            self._resetDropIndicator()
            return None, drop_item

        position = Position.kInside

        if not drop_item.isRoot():
            item_geo = self.itemTitleGeometry( drop_item )

            inside_rect = None
            if drop_item.type() == "group":
                threshold = item_geo.height() * .4
                inside_rect = QtCore.QRect( item_geo.x(), item_geo.y() + threshold, drop_item.selfGeometry().width(), drop_item.selfGeometry().height() - threshold )
                item_geo = inside_rect

            if not inside_rect or not inside_rect.contains( pos ):
                # If we drop outside the inside_rect or if the inside_rect is None (droping on a component)
                if pos.y() < item_geo.center().y():
                    position = Position.kAbove
                else:
                    position = Position.kUnder
            else:
                position = Position.kInside

        else:
            position = Position.kLast
            
        return position, drop_item
    
    def _buildSelectionData(self, inputItems=[]):
            
            if not inputItems:
                inputItems = self.flattenedSelection()
            
            dragData = []
            for item in inputItems:

                node = item.getNode()
                parent, index = node.parent()

                dragData.append( "%s,%s,%s" % ( node, parent, index ) )

            return "\n".join( dragData )

    def _buildDragPixmap( self, items ):

        items = list( items )

        if len( items ) == 1:
            return self._getWidgetPixmap( items[0] )

        # Sor the item frop top to bottom
        items.sort( key=lambda x: x.geometry().y() )

        pixmaps = []

        # Get all pixmaps
        for item in items:
            pixmaps.append( self._getWidgetPixmap( item ) )
        
        globalPixMap = QtGui.QPixmap( max( [ px.width() for px in pixmaps] ), sum( [px.height() for px in pixmaps] ) )
        globalPixMap.fill( QtGui.QColor( 0, 0, 0, 0 ) )

        painter = QtGui.QPainter( globalPixMap )

        pos = QtCore.QPoint()

        for pixmap in pixmaps:
            pos.setX( globalPixMap.width() - pixmap.width() )
            painter.drawPixmap( pos, pixmap )
            pos += QtCore.QPoint( 0, pixmap.height() )


        return globalPixMap

    def _getWidgetPixmap( self, item ):

        # Grab the widget
        pixmap = QtGui.QPixmap.grabWidget( item )

        # Build the alpha
        alpha_pixmap = QtGui.QPixmap( pixmap.width(), pixmap.height() )

        # First fill with black
        alpha_pixmap.fill( QtGui.QColor( 0, 0, 0 ) )

        # Then draw a grey rectangle for each child
        painter = QtGui.QPainter( alpha_pixmap )
        painter.setCompositionMode( painter.CompositionMode_SourceOver )
        for rect in item.getRectangles():
            painter.fillRect( rect, QtGui.QColor( 175, 175, 175 ) )
        painter.end()

        # Add the alpha
        pixmap.setAlphaChannel( alpha_pixmap )

        return pixmap

    def _drawDropIndicator( self, position=None, drop_item=None ):

        if isinstance( position, tuple ):
            drop_item = position[1]
            position = position[0]

        if position is None:
            return

        item_geo = None

        if drop_item.type() in ("root", "group"):
            if position == Position.kLast:
                lastIndex = drop_item.child_layout.count() - 1
                if lastIndex >= 0:
                    child = drop_item.child_layout.itemAt( lastIndex ).widget()
                    item_geo = drop_item.itemGeometry( child )
                else:
                    item_geo = drop_item.selfGeometry()
                    position = Position.kAbove
            else:
                item_geo = drop_item.selfGeometry()
        else:
            item_geo = drop_item.titleGeometry()

        self.drop_overlay_widget.setParent( drop_item )

        if position == Position.kInside:
            self.drop_overlay_widget.setGeometry( item_geo )
        elif position == Position.kAbove:
            self.drop_overlay_widget.setGeometry( item_geo.x(), item_geo.y(), item_geo.width(), 3 )
        elif position == Position.kUnder or position == Position.kLast:
            self.drop_overlay_widget.setGeometry( item_geo.x(), item_geo.y() + item_geo.height() - 3, item_geo.width(), 3 )

        self.drop_overlay_widget.setVisible( True )
        self.drop_overlay_widget.raise_()

    def _resetDropIndicator( self ):
        self.drop_overlay_widget.setParent( self )
        self.drop_overlay_widget.setGeometry( 0, 0, 0, 0 )
        self.drop_overlay_widget.hide()
        
    # ShortCuts ---
    
    @QtCore.Slot()
    def copySelectionToClipBoard(self):
        self._storeSelectionToClipboard()

    @QtCore.Slot()
    def cutSelectionToClipboard(self):
        self._storeSelectionToClipboard(erase=True)

    def _storeSelectionToClipboard(self, erase=False):
        # Feed the clipboard with the current selection
        
        clipboard = QtGui.QApplication.clipboard()
        clipboard.setText( self._buildSelectionData() )
        
        if erase:
            # We are cuting, delete the selected nodes
            for item in self.flattenedSelection():
                self.removeItem( item, delete_node=False )
                
    @QtCore.Slot()
    def pasteClipboard(self):
        
        clipboard = QtGui.QApplication.clipboard()
        
        clipboard_nodes = self._getDragData( clipboard )
        if clipboard_nodes:
            paste_destination = self.lastSelected()
            
            self.addItems( clipboard_nodes, paste_destination, behaviour=MoveBehaviour.kCopy )
        
    @QtCore.Slot()
    def duplicate(self):
        
        selectedNodes = self.flattenedSelection()
                
        if selectedNodes:
            # For every selected node, duplicate it above itself
            for node in selectedNodes:
                self.addItems( node, node, position=Position.kAbove, behaviour=MoveBehaviour.kCopy )
        
        
        


class TreeItemWidget( QtGui.QWidget ):

    def __repr__( self ):

        p = self.parent()
        index = p.child_layout.indexOf( self )

        return "%s(%s, %s, %s)" % ( type( self ).__name__, self.node().name(), p.node().name(), index )

    def __nonzero__( self ):
        return isValid( self ) and bool( QtGui.QWidget.parent( self ) )
    __bool__ = __nonzero__


    def __init__( self, input_, parent ):
        super( TreeItemWidget, self ).__init__( parent )

        self._node = mila_node( input_, create=True )

        self._selected = False
        
        self.setAcceptDrops( True )

        self.callBack = []

        icon_path = ICON( "%s.png" % self._node.nodeType() )

        self.main_layout = QtGui.QVBoxLayout( self )
        self.main_layout.setContentsMargins( 0, 0, 0, 0 )
        self.main_layout.setSpacing( 0 )

        self.title_widget = QtGui.QFrame( self )
        self.title_widget.setFixedHeight( 25 )
        self.title_widget.setContentsMargins( 0, 0, 0, 0 )
        self.title_widget.setFrameStyle( QtGui.QFrame.StyledPanel | QtGui.QFrame.Sunken )
        self.title_widget.setAutoFillBackground( True )
        pal = QtGui.QPalette()
        pal.setColor( QtGui.QPalette.Background, pal.window().color() )
        self.title_widget.setPalette( pal )

        # TITLE LAYOUT
        self.icon_widget = ColoredIcon( icon_path, ( 28, 28 ), self )

        self.createNodeCallBack()

        # LABEL (editable)
        self.label_widget = TreeItemWidgetLabel( self._node, self.title_widget )

        self.enable_widget = IconButton( QtGui.QPixmap( ICON( "green_dot.png" ) ), QtGui.QPixmap( ICON( "grey_dot.png" ) ) , self.title_widget )
        self.enable_widget.pressed.connect( self.enable_widget_clicked )

        self.solo_widget = IconButton( QtGui.QPixmap( ICON( "blue_dot.png" ) ), QtGui.QPixmap( ICON( "grey_dot.png" ) ) , self.title_widget, False )
        self.solo_widget.pressed.connect( self.solo_icon_clicked )
        self.solo_widget.setToolTip( "Solo" )

        self.delete_widget = IconButton( QtGui.QPixmap( ICON( "bin.png" ) ) , None, self.title_widget )
        self.delete_widget.pressed.connect( self.delete_button_clicked )

        self.titleLayout = QtGui.QHBoxLayout( self.title_widget )
        self.titleLayout.addWidget( self.icon_widget )
        self.titleLayout.addSpacing( 5 )
        self.titleLayout.addWidget( self.label_widget, stretch=True )
        self.titleLayout.addWidget( self.enable_widget )
        self.titleLayout.addWidget( self.solo_widget )
        self.titleLayout.addWidget( self.delete_widget )

        self.titleLayout.setContentsMargins( 8, 0, 0, 0 )
        self.titleLayout.setSpacing( 0 )

        self.main_layout.addWidget( self.title_widget )

        # Child layout (build under a simple widget for visibility purpose (and ease of deletion)
        self.child_widget = QtGui.QWidget( self )

        self.child_layout = QtGui.QVBoxLayout( self.child_widget )
        self.child_layout.setContentsMargins( 40, 0, 0, 5 )
        self.child_layout.setSpacing( 0 )

        self.child_widget.hide()

        self.main_layout.addWidget( self.child_widget )


        self.updateIconColor()
        
    def node(self):
        return self._node

    def matches( self, other ):
        try:
            return self.node() == other.node()
        except AttributeError:
            return False

    def createNodeCallBack( self ):
        # Add a callback to update the icon color
        self.callBack.append( OpenMaya.MNodeMessage.addAttributeChangedCallback( self.node().obj, self.colorChangeCallback ) )
        # Add a callback to delete all callback when the node is going to be deleted
        self.callBack.append( OpenMaya.MNodeMessage.addNodePreRemovalCallback( self.node().obj, self.nodeDeletedCallback ) )

    def deleteLater( self, *args, **kargs ):
        self.deleteAllCallback()
        super( TreeItemWidget, self ).deleteLater( *args, **kargs )

    def updateIconColor( self ):
        try:
            color = cmds.getAttr( self.node().attr( "tint" ) )[0]
        except ValueError:
            return

        self.icon_widget.setColor( *color )

    def colorChangeCallback( self, msg, thisPlug, otherPlug, *args ):
        try:
            if ( thisPlug.name().endswith( "tint" ) ):
                self.updateIconColor()
        except RuntimeError:
            # Something went wrong with the callback, delete them
            self.deleteAllCallback()
            
    def nodeDeletedCallback(self, *args):
        print "DeleteCallback for %r" % self
        self.deleteAllCallback()
        self.delete(delete_node=False)

    def deleteAllCallback( self, *args ):
        for callback in self.callBack:
            try:
                OpenMaya.MMessage.removeCallback( callback )
            except RuntimeError:
                pass
        self.callBack = []

    def getNode( self ):

        p = self.parent()
        
        new_node = copy.copy( self.node() )
        
        if p:
            uiId = p.child_layout.indexOf( self )
            nodeId = p.node().connectedIndices()[uiId]

            new_node._parent = p.node()
            new_node._parent_id = nodeId
        else:
            new_node._parent = None
            new_node._parent_id = None

        return new_node

    def isRoot( self ):
        return False

    def root( self ):
        parent = self
        while not parent.isRoot():
            parent = parent.parent()

        return parent

    def type( self ):
        return self.node().type()

    def nodeType( self ):
        return self.node().nodeType()

    def parent( self ):
        parent = QtGui.QWidget.parent( self )
        while not isinstance( parent, ( type( self ), TreeWidget ) ):
            parent = QtGui.QWidget.parent( parent )
        return parent

    def index( self ):
        # Returns the index this item has inside his parent layout
        # Returns -1 if the item has no parent layout
        try:
            return self.parent().child_layout.indexOf( self )
        except Exception:
            return -1

    def delete( self, delete_node=True ):
        self.root().removeItem( self, delete_node )

    def clear( self ):

        # Delete Qt layout"
        child = self.child_layout.takeAt( 0 )
        while child:
            widget = child.widget()
            if widget:
                widget.deleteLater()
                del widget
            child = self.child_layout.takeAt( 0 )

    def setSoloState( self, value=True ):
        self.solo_widget.setState( value )

    def setState( self, value=None, set=False ):

        if value is None:
            value = self.node().enabled()

        self.enable_widget.setState( value )

        if set:
            with UndoChunk( "mila_enable_node( %s, value=%s )" % ( self.node().name(), value ) ):
                mila_enable_node( self.node(), value=value )

    def setSolo( self, value=True, set=False ):

        if value:
            self.setSoloState( True )

            if set:
                self.root().resetSolo( self, True )
                with UndoChunk( "mila_set_solo(%s,%s)" % ( self.node().name(), self.root().mila().name() ) ):
                    mila_set_solo( self.node(), self.root().mila() )
        else:
            self.setSoloState( False )
            if set:
                self.root().resetSolo( self, False )
                with UndoChunk( "mila_remove_solo(%s)" % self.root().mila().name() ):
                    mila_remove_solo( self.root().mila() )

    @QtCore.Slot()
    def solo_icon_clicked( self ):
        state = self.solo_widget.state()
        self.setSolo( value=not state, set=True )

    @QtCore.Slot()
    def enable_widget_clicked( self ):
        state = self.node().enabled()
        self.setState( value=not state, set=True )

    @QtCore.Slot()
    def delete_button_clicked( self ):
        self.delete()

    def children( self ):
        return self.findChildren( type( self ) )

    def relativeGeometry( self, relativeTo ):
        return self.geometry().translated( self.mapTo( relativeTo, self.geometry().topLeft() ) )

    def getRectangles( self, relativeTo=None ):

        if relativeTo == None:
            relativeTo = self

        for item in self.children():

            yield item.titleGeometry().translated( item.mapTo( relativeTo, item.titleGeometry().topLeft() ) )

        yield self.titleGeometry()

    def selfGeometry( self ):
        geo = self.geometry()
        return QtCore.QRect( 0, 0, geo.width(), geo.height() )

    def titleGeometry( self ):
        return self.title_widget.geometry()

    def clickableGeometry( self ):

        geo = self.geometry()
        width = self.icon_widget.geometry().width() + self.label_widget.geometry().width()

        return QtCore.QRect( 0, 0, width, geo.height() )

    def buttonGeometry( self ):

        geo = self.geometry()
        width = self.icon_widget.geometry().width() + self.label_widget.geometry().width()

        return QtCore.QRect( width, 0, self.geometry().right(), geo.height() )

    def showChildLayout( self, value=True ):
        if self.node().type() == "component":
            value = False
        self.child_widget.setVisible( value )

    def collapse( self ):
        self.showChildLayout( False )

    def collapsed( self ):
        return not self.child_widget.isVisible()

    def expand( self ):
        self.showChildLayout( True )

    def expanded( self ):
        return self.child_widget.isVisible()

    def selected( self ):
        return self._selected

    def _selectedColor( self ):
        pal = QtGui.QPalette()
        typo_pal = QtGui.QPalette()

        return  pal.highlight().color(), pal.highlightedText().color()

    def _idleColor( self ):
        pal = QtGui.QPalette()
        typo_pal = QtGui.QPalette()

        return  pal.window().color(), pal.text().color()

    def _selectedHintColor( self ):
        pal = QtGui.QPalette()
        typo_pal = QtGui.QPalette()

        ratio = .35

        def mixColor( color1, color2, r ):

            return QtGui.QColor( color1.red() * ( 1 - r ) + color2.red() * r,
                                 color1.green() * ( 1 - r ) + color2.green() * r,
                                 color1.blue() * ( 1 - r ) + color2.blue() * r )


        idleColor, idleTypo = self._idleColor()
        selectedColor, selectedTypo = self._selectedColor()

        hintColor = mixColor( idleColor, selectedColor, ratio )
        hintText = mixColor( idleTypo, selectedTypo, ratio )

        return  hintColor, hintText

    def _setColor( self, colorName ):

        pal = QtGui.QPalette()
        typo_pal = QtGui.QPalette()

        color, typo_color = None, None

        if colorName == "selected":
            color, typo_color = self._selectedColor()
        elif colorName == "idle":
            color, typo_color = self._idleColor()
        elif colorName == "selectHint":
            color, typo_color = self._selectedHintColor()

        pal.setColor( QtGui.QPalette.Background, color )
        typo_pal.setColor( QtGui.QPalette.Text, typo_color )

        self.title_widget.setPalette( pal )
        self.label_widget.setPalette( typo_pal )


    def setSelectHint( self, state ):

        if state and not self.selected():
            self._setColor( "selectHint" )
        else:
            if self.selected():
                self._setColor( "selected" )
            else:
                self._setColor( "idle" )


    def select( self, state=True ):

        self._selected = state
        if state:
            self._setColor( "selected" )
        else:
            self._setColor( "idle" )



class TreeItemWidgetLabel( QtGui.QWidget ):

    def __init__( self, node, parent ):
        super( TreeItemWidgetLabel, self ).__init__( parent )

        self._node = node

        self.mainLayout = QtGui.QHBoxLayout( self )
        self.mainLayout.setContentsMargins( 0, 0, 0, 0 )
        self.mainLayout.setSpacing( 0 )

        # Display Widget
        self.displayWidget = QtGui.QFrame( self )

        self.displayLayout = QtGui.QVBoxLayout( self.displayWidget )
        self.displayLayout.setContentsMargins( 0, 0, 0, 0 )
        self.displayLayout.setSpacing( 0 )

        self.niceName = QtGui.QLabel( self._node.niceName() , self.displayWidget )

        self.realName = QtGui.QLabel( self._node.name(), self.displayWidget )
        widgetFont = QtGui.QFont()
        widgetFont.setPointSize( 6 )
        self.realName.setFont( widgetFont )

        self.displayLayout.addWidget( self.niceName )
        self.displayLayout.addWidget( self.realName )

        # Edit Widget (hidden by default)
        self.editWidget = QtGui.QFrame( self )
        self.editLayout = QtGui.QVBoxLayout( self.editWidget )
        self.editLayout.setContentsMargins( 0, 0, 0, 0 )
        self.editLayout.setSpacing( 0 )
        self.lineEdit = QtGui.QLineEdit( self.editWidget )
        self.editLayout.addWidget( self.lineEdit )

        self.lineEdit.editingFinished.connect( self.editNiceName )

        self.editWidget.hide()

        self.mainLayout.addWidget( self.displayWidget, True )
        self.mainLayout.addWidget( self.editWidget )

        self.update()
        
    def node(self):
        return self._node

    def mouseDoubleClickEvent( self, event ):

        newName = self.niceName.text().strip()

        self.displayWidget.hide()
        self.editWidget.show()
        self.lineEdit.setFocus()
        self.lineEdit.setText( self.niceName.text() )
        self.lineEdit.selectAll()

        event.accept()

    def update( self ):

        if not self.node().niceName() or self.node().niceName() == self.node().name():
            self.realName.hide()
        else:
            self.realName.show()

    @QtCore.Slot()
    def editNiceName( self ):

        newName = self.lineEdit.text().strip()

        self.niceName.setText( newName )
        self.displayWidget.show()
        self.editWidget.hide()

        self.node().setNiceName( newName )

        self.update()


class ComponentCreatorButton( QtGui.QPushButton ):

    clicked = QtCore.Signal( str )

    def __init__( self, item_name, parent ):
        super( ComponentCreatorButton, self ).__init__( parent )

        self.setIcon( QtGui.QIcon( ICON( "%s.png" % item_name ) ) )
        self.setFlat( True )

        self.data = item_name

        self.toolTipStr = mila_nice_name( item_name )

        self.setMouseTracking( True )

        self.setFixedSize( 22, 22 )

    def mouseMoveEvent( self, event ):

        event.accept()
        QtGui.QToolTip.showText( event.globalPos(), self.toolTipStr, self )
        
        
        if QtGui.QApplication.mouseButtons() == QtCore.Qt.LeftButton:
            
            # Only start the drag si he mouse leaves the button
            if not QtCore.QRect( 0, 0, self.width(), self.height() ).contains( event.pos() ):
                
                #  Create the node, we will delete it if the drag is not completed
                node = mila_node(self.data, create=True)
                
                dragData = node.name()
    
                mimeData = QtCore.QMimeData()
                mimeData.setText( dragData )
                
                # Grab the widget
                pixmap = QtGui.QPixmap.grabWidget( self )
    
                drag = QtGui.QDrag( self )
                drag.setMimeData( mimeData )
                drag.setPixmap( pixmap )
    
                if drag.start( QtCore.Qt.MoveAction ) == QtCore.Qt.IgnoreAction:
                    cmds.delete( node )
                    
                # We clicked on the item, set it back to the up position
                self.setDown(False)
                

    def mouseReleaseEvent( self, event ):

        if QtCore.QRect( 0, 0, self.width(), self.height() ).contains( event.pos() ):
            self.clicked.emit( self.data )

        QtGui.QPushButton.mouseReleaseEvent( self, event )



class IconButton( QtGui.QLabel ):

    pressed = QtCore.Signal()

    def __init__( self, icon_on, icon_off, parent, defaultValue=True ):
        super( IconButton, self ).__init__( "", parent )

        self.on = icon_on
        if icon_off:
            self.off = icon_off
        else:
            self.off = self.on

        self.setMinimumWidth( 20 )

        self.setState( defaultValue )

    def mousePressEvent( self, event ):

        event.accept()

        if event.buttons() == QtCore.Qt.LeftButton:
            self.pressed.emit()
        else:
            return
        
    def state( self ):

        return self.state_value

    def setState( self, value ):

        self.state_value = value

        if value:
            self.setPixmap( self.on )
        else:
            self.setPixmap( self.off )


class ColoredIcon( QtGui.QLabel ):

    def __init__( self, fileName, size, parent ):

        super( ColoredIcon, self ).__init__( parent )

        self.orig_image = QtGui.QImage( fileName )

        self.orig_image = self.orig_image.scaled( size[0], size[1], QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation )

        self._setPixmap( self.orig_image )

    def setColor( self, *args ):

        color = None
        color_add = None

        if len( args ) == 3:
            # If any channel is above 1, we will multiply by one and add anything above 1 (to show the overbright color)

            rgb = [ float( args[0] ), float( args[1] ), float( args[2] ) ]

            rgb_add = [0.0, 0.0, 0.0]

            for i in range( len( rgb ) ):
                if rgb[i] > 1.0:
                    rgb_add[i] = min( ( rgb[i] - 1.0 ), 1.0 )
                    rgb[i] = 1.0

            color = QtGui.QColor()
            color.setRgbF( *rgb )

            if any( rgb_add ):
                color_add = QtGui.QColor()
                color_add.setRgbF( *rgb_add )

        # If the color is white, set the default icon
        if color_add is None and ( color is None or color == "white" ):
            self.setPixmap( QtGui.QPixmap.fromImage( self.orig_image ) )
            return


        new_image = self.orig_image.copy()

        painter = QtGui.QPainter()
        painter.begin( new_image )
        painter.setCompositionMode( QtGui.QPainter.CompositionMode_Multiply )
        painter.fillRect( new_image.rect(), color )

        if color_add:
            painter.setCompositionMode( QtGui.QPainter.CompositionMode_Plus )
            painter.fillRect( new_image.rect(), color_add )
        painter.end()


        new_image.setAlphaChannel( self.orig_image.alphaChannel() )

        self.setPixmap( QtGui.QPixmap.fromImage( new_image ) )

    def _setPixmap( self, image ):

        self.setPixmap( QtGui.QPixmap.fromImage( image ) )
        

class AutoHideMenu(QtGui.QMenu):
    
    def __init__(self, parent):
        super( AutoHideMenu, self ).__init__( parent)
        
    def mouseReleaseEvent(self, event):
        
        action = self.actionAt(event.pos())
        
        if action:
            action.triggered.emit()
        self.close()


## BASE Maya function ---
## This is where the modification to the DG is performed

def set_widget_name( object, name ):

    # We will use the maya naming convention, we use the class name followed by a number to ensure unique name
    name = str( name )

    ptr = True
    i = 0
    while ptr:
        i += 1
        ptr = OpenMayaUI.MQtUtil.findControl( name + str( i ) )

    object.setObjectName( name + str( i ) )


def set_layout_name( object, name ):
    name = str( name )

    ptr = True
    i = 0
    while ptr:
        i += 1
        ptr = OpenMayaUI.MQtUtil.findLayout( name + str( i ) )

    object.setObjectName( name + str( i ) )


def mila_nice_name( milaName ):

    nicename = ""

    for item in milaName.split( "_" )[1:]:
        nicename += item.title() + " "

    return nicename.strip()


def mila_tree( mila=None, parent=None ):
    
    if parent is None:
        win = cmds.window( "MilaTree - %s" % mila )
        parent = cmds.columnLayout( adj=True )
        cmds.setParent( ".." )
        cmds.showWindow( win )


    ptr = OpenMayaUI.MQtUtil.findLayout( parent )
    parentWidget = wrapInstance( long( ptr ), QtGui.QWidget )

    mila_ui = MilaTreeLayout( mila, parentWidget )

    parentWidget.layout().addWidget( mila_ui )

    cmds.setParent( parent )

    # If the parent is the Attribute Editor or the property editor, we need to keep track of our QObject for later updates
    # e.g. when we select another node
    if "MainAttributeEditorLayout" in parent or "propertyPanelForm" in parent:
        # We will save the MilaTreeLayout
        global AE_MILA_UI
        AE_MILA_UI[parent] = mila_ui


    return mila_ui.fullName()


def mila_tree_update_AE( mila, parent=None ):

    global AE_MILA_UI

    if not parent in AE_MILA_UI:
        return

    if mila != AE_MILA_UI[parent].treeUI.mila().name():
        # It's a different mila, change the ui and reload it
#         print "%s: It's a different mila, change the ui and reload it" % mila
        AE_MILA_UI[parent].treeUI.setMila( mila )
#     elif not cmds.connectionInfo( "%s.shader" % mila, isExactDestination=True ):
#         # it's the same mila but it has not incoming connection. something was broken by te user
#         print "%s: it's the same mila but it has not incoming connection" % mila
#         AE_MILA_UI[parent].treeUI.initializeMila()
        
