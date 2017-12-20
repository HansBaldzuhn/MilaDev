# -*- coding: utf-8 -*-
from PySide import QtGui, QtCore

import maya.cmds as cmds
import maya.utils
import maya.OpenMayaUI as OpenMayaUI
from shiboken import wrapInstance
import math

columnWidthData = [( 1, 80 ), ( 3, 10 )]
columnWidthData2 = [( 1, 80 ), ( 2, 10 )]
columnWidthData3 = [( 1, 80 )]

def schlickFresnel( x, min=0.01, max=1.0, coef=5, *args ):

	x = math.radians( x )
	y = min + ( 1 * max - min ) * ( ( 1 - math.cos( x ) ) ** coef )
	if y < 0:
		return 0
	return y

def exactFresnel( x, ior=1.33 ):

	x = math.radians( x )

	cosX = math.cos( x )
	sinX = math.sin( x )
	tanX = math.tan( x )

	a = math.sqrt( ior ** 2 - sinX ** 2 )

	Fs = ( a ** 2 - 2 * a * cosX + cosX ** 2 ) / ( a ** 2 + 2 * a * cosX + cosX ** 2 )

	b = 2 * a * sinX * tanX
	c = sinX ** 2 * tanX ** 2

	d = b + c

	Fp = Fs * ( a ** 2 - b + c ) / ( a ** 2 + b + c )

	F = ( Fs + Fp ) / 2

	return F

class GraphWidget( QtGui.QWidget ):

	def __init__( self, func=None, rangeX=[], rangeY=[], *args ):
		super( GraphWidget, self ).__init__( *args )

		if func:
			self.func = func

		self.rangeX = rangeX
		self.rangeY = rangeY

		self.cmdArgs = []

		self.margin = 1

		self.setName()

		self.setMinimumSize( 45, 60 )
		self.pal = QtGui.QPalette()

	def fullName( self ):
		ptr = OpenMayaUI.MQtUtil.findControl( self.objectName() )
		return OpenMayaUI.MQtUtil.fullName( long( ptr ) )

	def setName( self ):
		from mila_material_ui import set_widget_name
		set_widget_name( self, "fresnelGraphWidget" )

	def rect2( self ):
		return QtCore.QRect( self.margin, self.margin, self.width() - self.margin * 2, self.height() - self.margin * 2 )

	def width2( self ):
		return self.width() - self.margin

	def height2( self ):
		return self.height() - self.margin

	def paintEvent( self, paintEvent ):

		painter = QtGui.QPainter( self )

		try:
			painter.fillRect( self.rect2(), self.pal.base().color() )

			painter.setPen( self.pal.dark().color() )
			painter.drawRect( self.rect2() )

			painter.setPen( self.pal.text().color() )

			path = QtGui.QPainterPath()

			cmd = path.moveTo

			for px in range( self.rect().width() ):

				# Get the requested x value
				x = self.coordX( px )

				# compute y
				try:
					y = self.func( x, *self.cmdArgs )
				except Exception:
					cmd = path.moveTo
					continue

				# now remap y in pixel
				py = self.coordY( y )

				cmd( px, py )

				if py < 0 or py > self.height2():
					cmd = path.moveTo
				else:
					cmd = path.lineTo

			painter.drawPath( path )
		finally:
			painter.end()

	@QtCore.Slot( object )
	def setArgs( self, *args ):
# 		if not isinstance(args,(list,tuple)):
# 			args = (args,)

		args = [float( val ) for val in args]

		self.cmdArgs = args
		self.update()

	@QtCore.Slot( int )
	def setRangeX( self, value ):
		max = abs( float( value ) )
		self.rangeX = [max, -max]

		self.update()

	@QtCore.Slot( int )
	def setRangeY( self, value ):
		max = abs( float( value ) )
		self.rangeY = [max, -max]
		self.update()

	def setFunc( self, func ):
		self.func = func
		self.update()

	def coordX( self, x ):

		min = float( self.rangeX[0] )
		max = float( self.rangeX[1] )
		# remap input going from 0 to self.width() to a range from -1 to 1
		# First remap to 0 -> 2 then substract 1
		return ( x * ( max - min ) / self.width2() ) + min

	def coordY( self, val ):
		min = float( self.rangeY[0] )
		max = float( self.rangeY[1] )

		coord = ( ( val - min ) * self.height2() ) / ( max - min )

		# Pyside coord start from the top, we need to reverse the value
		return self.height2() - coord


	def func( self, x ):
		# Default function, doing nothing ><
		return x

def graphWidgetUI():

	parent = cmds.setParent( q=True )

	ptr = OpenMayaUI.MQtUtil.findLayout( parent )
	parentWidget = wrapInstance( long( ptr ), QtGui.QWidget )

	graphUI = GraphWidget( schlickFresnel, [0, 90], [0, 1], parentWidget )
	graphUI.setArgs( .05, 1.0, 5 )

	parentWidget.layout().addWidget( graphUI )

	return graphUI


class AE_mila_base_ui( object ):

	def __init__( self, node=None, node_parent=None ):

		self.parentData = {}
		self.controlData = {}

		# Mix of Layer item
		self.tabLayout = cmds.tabLayout( childResizable=True, tabsVisible=False )
		cmds.setParent( ".." )

		# Component Items
		self.tabLayoutComponent = cmds.tabLayout( childResizable=True, tabsVisible=False )
		cmds.setParent( ".." )


	def setNode( self, node ):

		cmds.tabLayout( self.tabLayoutComponent, edit=True, manage=True )

		nodeType = cmds.nodeType( node )

		data = {}

		# Build the tab if it doesn't already exist
		if nodeType in self.controlData:
			data = self.controlData[nodeType]

		else:
			if cmds.setParent( self.tabLayoutComponent ):

				layout = cmds.columnLayout( adj=True )

				obj = AE_mila_component_template( node )

				data["obj"] = obj
				data["ui"] = layout
				self.controlData[nodeType] = data

				cmds.setParent( ".." )
			cmds.setParent( ".." )

		data["obj"].update( node )

		self._setTab( self.tabLayoutComponent, data )


	def setParentNode( self, node ):

		cmds.tabLayout( self.tabLayout, edit=True, manage=True )

		nodeType = cmds.nodeType( node )

		data = {}

		# Build the tab if it doesn't already exist
		if nodeType in self.parentData:
			data = self.parentData[nodeType]

		else:
			if cmds.setParent( self.tabLayout ):

				layout = cmds.columnLayout( adj=True )
				obj = AE_mila_component_template( node )

				data["obj"] = obj
				data["ui"] = layout
				self.parentData[nodeType] = data

				cmds.setParent( ".." )
			cmds.setParent( ".." )

		data["obj"].update( node )

		self._setParentTab( self.tabLayout, data )

	def hide( self ):
		self.hideNode()
		self.hideParentNode()

	def hideNode( self ):
		cmds.tabLayout( self.tabLayoutComponent, edit=True, manage=False )

	def hideParentNode( self ):
		cmds.tabLayout( self.tabLayout, edit=True, manage=False )


	def _setTab( self, tabLayout, childObj ):

		# Disable All ui before switching to ensure the layout is as small as possible
		for key, item in self.controlData.items():
			cmds.layout( item["obj"].layout, edit=True, manage=False )

		# Now display the one we will be showing
		cmds.layout( childObj["obj"].layout, edit=True, manage=True )

		cmds.tabLayout( self.tabLayoutComponent, edit=True, selectTab=childObj["ui"] )

	def _setParentTab( self, tabLayout, childObj ):

		# Disable All ui before switching to ensure the layout is as small as possible
		for key, item in self.parentData.items():
			cmds.layout( item["obj"].layout, edit=True, manage=False )

		# Now display the one we will be showing
		cmds.layout( childObj["obj"].layout, edit=True, manage=True )

		cmds.tabLayout( self.tabLayout, edit=True, selectTab=childObj["ui"] )



class AE_mila_base_template( object ):

	def __init__( self, node ):

		self.node = None
		self.setNode( node )

		self.controls = []
		self.connectControls = []
		self.scriptJobs = []

		oldParent = cmds.setParent( query=True )

		self.layout = cmds.columnLayout( adj=True )
		cmds.setParent( self.layout )


	def attr( self, attr ):
		return "%s.%s" % ( self.node, attr )

	def addControl( self, *args ):
		if len( args ) == 1:
			self.controls.append( *args )
		else:
			self.controls.append( args )

	def addControlGrp( self, input ):
		pass

	def setNode( self, node ):

		self.node = node

	def update( self, node ):

		self.setNode( node )

		nodeType = cmds.nodeType( self.node )

		# Connect all attributes of the current node to the corresponding control
		for item in self.connectControls:

			attr, control = item[:2]
			index = None

			try:
				index = item[2]
			except IndexError:
				pass

			attribute = self.attr( attr )

			enable = cmds.objExists( attribute )

			if enable:
				if index:
					cmds.connectControl( control, attribute, index=index )
				else:
					cmds.connectControl( control, attribute )

			cmds.control( control, edit=True, manage=enable )

		for item in self.controls:
			attr, control, cmd = item[:3]
			index = None

			attribute = self.attr( attr )

			enable = cmds.objExists( attribute )

			if enable:
				cmd( control, edit=True, attribute=attribute )

			cmds.control( control, edit=True, manage=enable )

		# Update all scriptJob to target the correct node
		for item in self.scriptJobs:

			attr, parentControl, scriptJobArg, cmd = item
			attribute = self.attr( attr )

			kargs = {scriptJobArg: ( attribute, cmd )}

			cmds.scriptJob( replacePrevious=True, parent=parentControl, **kargs )


class AE_bump_template( AE_mila_base_template ):
	def __init__( self, node, collapse=True ):
		super( AE_bump_template, self ).__init__( node )

		if cmds.frameLayout( label="Bump", collapse=True, collapsable=True ):
			if cmds.columnLayout( adj=True ):

				self.bump = cmds.attrNavigationControlGrp( attribute=self.attr( "bump" ), label="Bump", columnWidth=columnWidthData2, adj=2 )
				self.addControl( "bump", self.bump, cmds.attrNavigationControlGrp )

				self.scriptJobA = cmds.scriptJob( replacePrevious=True, parent=self.bump, connectionChange=( self.attr( "bump" ), self.updateBumpControl ) )
				self.scriptJobs.append( ( "bump", self.bump, "connectionChange", self.updateBumpControl ) )

				self.columnLayout = cmds.columnLayout( adj=True, manage=False )

				cmds.setParent( ".." )

			cmds.setParent( ".." )
		cmds.setParent( ".." )

		self.updateBumpControl()

	def updateBumpControl( self ):
		# We were unable to set the values, something must be plugin, get it and build controls for it
		nodeAttr = cmds.connectionInfo( self.attr( "bump" ), sfd=True )

		if not nodeAttr:
			cmds.setAttr( self.attr( "bump" ), 0, 0, 0 )
			cmds.columnLayout( self.columnLayout, edit=True, manage=False )
			return

		for child in cmds.layout( self.columnLayout, query=True, childArray=True ) or []:
			cmds.deleteUI( child )

		node = nodeAttr.split( "." )[0]
		self.value = cmds.attrFieldSliderGrp( attribute="%s.bumpValue" % node, label="Bump Value", columnWidth=columnWidthData, parent=self.columnLayout )
		self.depth = cmds.attrFieldSliderGrp( attribute="%s.bumpDepth" % node, label="Bump Depth", columnWidth=columnWidthData, parent=self.columnLayout )
		try:
			self.interp = cmds.attrEnumOptionMenuGrp( attribute="%s.bumpInterp" % node, label="Use As:", columnWidth=columnWidthData3, parent=self.columnLayout )
		except:
			pass

		cmds.columnLayout( self.columnLayout, edit=True, manage=True )

	def update( self, node ):
		super( AE_bump_template, self ).update( node )

		self.updateBumpControl()


class AE_mila_layer_template( AE_mila_base_template ):

	def __init__( self, node ):

		super( AE_mila_layer_template, self ).__init__( node )

		# LAYER / MIX
		if cmds.frameLayout( label="Layer", collapsable=True ):
			if cmds.columnLayout( adj=True ):

# 				self.on = cmds.attrControlGrp( attribute = self.attr("on"))

				self.weight = cmds.attrFieldSliderGrp( attribute=self.attr( "weight" ), label="Weight", columnWidth=columnWidthData )
				self.addControl( "weight", self.weight, cmds.attrFieldSliderGrp )

				self.weight_tint = cmds.attrColorSliderGrp( attribute=self.attr( "weight_tint" ), label="Weight Tint", columnWidth=columnWidthData )
				self.addControl( "weight_tint", self.weight_tint, cmds.attrColorSliderGrp )

				self.fresnelLayout = cmds.formLayout()
				if self.fresnelLayout:

					self.directionalWeight = cmds.optionMenuGrp( label="Fresnel", columnWidth=columnWidthData, cc=self._setDirectionalMode )
					if self.directionalWeight:
						cmds.menuItem( "Constant" )
						cmds.menuItem( "IOR" )
						cmds.menuItem( "Custom" )


					self.scriptJobA = cmds.scriptJob( replacePrevious=True, parent=self.directionalWeight, attributeChange=( self.attr( "directional_weight_mode" ), self._directionalModeChanged ) )
					self.scriptJobB = cmds.scriptJob( replacePrevious=True, parent=self.fresnelLayout, attributeChange=( self.attr( "use_directional_weight" ), self._directionalModeChanged ) )

					self.scriptJobs.append( ( "directional_weight_mode", self.directionalWeight, "attributeChange", self._directionalModeChanged ) )
					self.scriptJobs.append( ( "use_directional_weight", self.fresnelLayout, "attributeChange", self._directionalModeChanged ) )

					self.showCurve = cmds.checkBox( label="Show Curve", cc=self._showCurveChanged, width=10, value=True )

					self.ior = cmds.attrFieldSliderGrp( attribute=self.attr( "ior" ), label="IOR", columnWidth=columnWidthData,
													cc=self.iorFresnelChanged )
					self.addControl( "ior", self.ior, cmds.attrFieldSliderGrp )

					self.normal_reflectivity = cmds.attrFieldSliderGrp( attribute=self.attr( "normal_reflectivity" ), label="0 degree", columnWidth=columnWidthData,
																	cc=self.customFresnelChanged )
					self.addControl( "normal_reflectivity", self.normal_reflectivity, cmds.attrFieldSliderGrp )

					self.grazing_reflectivity = cmds.attrFieldSliderGrp( attribute=self.attr( "grazing_reflectivity" ), label="90 degree", columnWidth=columnWidthData,
																		cc=self.customFresnelChanged )
					self.addControl( "grazing_reflectivity", self.grazing_reflectivity, cmds.attrFieldSliderGrp )

					self.exponent = cmds.attrFieldSliderGrp( attribute=self.attr( "exponent" ), label="Exponent", columnWidth=columnWidthData,
															cc=self.customFresnelChanged )
					self.addControl( "exponent", self.exponent, cmds.attrFieldSliderGrp )

					col = cmds.columnLayout( adj=True )
					if col:
						self.graphWidget = graphWidgetUI()
					cmds.setParent( ".." )

				cmds.setParent( ".." )

				cmds.formLayout( self.fresnelLayout, edit=True,

								attachForm=[
											[self.directionalWeight, "top", 2],
											[self.directionalWeight, "left", 0],

											[self.showCurve, "top", 2],
											[self.showCurve, "right", 0],

											[self.ior, "left", 0],

											[self.normal_reflectivity, "left", 0],

											[self.grazing_reflectivity, "left", 0],

											[self.exponent, "left", 0],

											[col, "right", 12],
											[col, "bottom", 10],
											[col, "left", 190]
										   ],
								attachControl=[

											[self.showCurve, "left", 2, self.directionalWeight],
											[col, "top", 4, self.showCurve],

											[self.ior, "top", 2, self.directionalWeight],

											[self.normal_reflectivity, "top", 2, self.directionalWeight],

											[self.grazing_reflectivity, "top", 2, self.normal_reflectivity],
											[self.exponent, "top", 2, self.grazing_reflectivity],

										   ],
								attachNone=[
											[self.directionalWeight, "right"],
											[self.directionalWeight, "bottom"],

											[self.showCurve, "bottom"],

											[self.ior, "bottom"],
											[self.ior, "right"],

											[self.normal_reflectivity, "right"],
											[self.normal_reflectivity, "bottom"],

											[self.grazing_reflectivity, "right"],
											[self.grazing_reflectivity, "bottom"],

											[self.exponent, "right"],
											[self.exponent, "bottom"]
										   ],
								)


				self.bump = AE_bump_template( self.node )

			cmds.setParent( ".." )
		cmds.setParent( ".." )

		self._directionalModeChanged()

	def update( self, node ):
		super( AE_mila_layer_template, self ).update( node )

		self.bump.update( node )
		self._directionalModeChanged()

	def _showCurveChanged( self, *args ):

		self.graphWidget.setVisible( False )
		cmds.refresh()
		def cmd( obj ):
			value = cmds.checkBox( obj.showCurve, query=True, value=True ) and cmds.getAttr( obj.attr( "use_directional_weight" ) )
			self.graphWidget.setVisible( value )
			cmds.refresh()

		self.graphWidget.update()

		maya.utils.executeDeferred( cmd, self )

	def customFresnelChanged( self, *args ):

		self.graphWidget.setFunc( schlickFresnel )

		facing = cmds.getAttr( self.attr( "normal_reflectivity" ) )
		grzing = cmds.getAttr( self.attr( "grazing_reflectivity" ) )
		expo = cmds.getAttr( self.attr( "exponent" ) )

		self.graphWidget.setArgs( facing, grzing, expo )

	def iorFresnelChanged( self, *args ):

		self.graphWidget.setFunc( exactFresnel )

		ior = cmds.getAttr( self.attr( "ior" ) )

		self.graphWidget.setArgs( ior )


	def _directionalModeChanged( self, *args ):

		customShow = False
		iorShow = False

		use_directional_weight = cmds.getAttr( self.attr( "use_directional_weight" ) )

		# Simple case, we don't use directionl weight
		if not use_directional_weight:

			cmds.optionMenuGrp( self.directionalWeight, edit=True, value="Constant" )

		else:
			# Get the diretionnal mode
			mode = cmds.getAttr( self.attr( "directional_weight_mode" ) )
			if mode == 0:
				self.iorFresnelChanged()
				cmds.optionMenuGrp( self.directionalWeight, edit=True, value="IOR" )
				iorShow = True
			else:
				self.customFresnelChanged()
				cmds.optionMenuGrp( self.directionalWeight, edit=True, value="Custom" )
				customShow = True

		cmds.control( self.showCurve, edit=True, enable=use_directional_weight )

		cmds.control( self.normal_reflectivity, edit=True, visible=customShow )
		cmds.control( self.grazing_reflectivity, edit=True, visible=customShow )
		cmds.control( self.exponent, edit=True, visible=customShow )

		cmds.control( self.ior, edit=True, visible=iorShow )

		self._showCurveChanged()


	def _setDirectionalMode( self, *args ):

		customShow = False
		iorShow = False

		mode = cmds.optionMenuGrp( self.directionalWeight, query=True, value=True )

		if mode == "Constant":
			cmds.setAttr( self.attr( "use_directional_weight" ), False )
		elif mode == "IOR":
			cmds.setAttr( self.attr( "use_directional_weight" ), True )
			cmds.setAttr( self.attr( "directional_weight_mode" ), 0 )
			iorShow = True
		elif mode == "Custom":
			cmds.setAttr( self.attr( "use_directional_weight" ), True )
			cmds.setAttr( self.attr( "directional_weight_mode" ), 1 )
			customShow = True

		cmds.control( self.normal_reflectivity, edit=True, visible=customShow )
		cmds.control( self.grazing_reflectivity, edit=True, visible=customShow )
		cmds.control( self.exponent, edit=True, visible=customShow )

		cmds.control( self.ior, edit=True, visible=iorShow )


class AE_mila_mix_template( AE_mila_base_template ):

	def __init__( self, node ):

		super( AE_mila_mix_template, self ).__init__( node )

		self.setNode( node )

		# LAYER / MIX
		if cmds.frameLayout( label="Mix", collapsable=True ):
			if cmds.columnLayout( adj=True ):

# 				self.on = cmds.attrControlGrp( attribute = self.attr("on"))

				self.weight = cmds.attrFieldSliderGrp( attribute=self.attr( "weight" ), label="Weight", columnWidth=columnWidthData )
				self.addControl( "weight", self.weight, cmds.attrFieldSliderGrp )

				self.weight_tint = cmds.attrColorSliderGrp( attribute=self.attr( "weight_tint" ), label="Tint", columnWidth=columnWidthData )
				self.addControl( "weight_tint", self.weight_tint, cmds.attrColorSliderGrp )

				self.bump = AE_bump_template( self.node )

			cmds.setParent( ".." )
		cmds.setParent( ".." )

	def update( self, node ):
		super( AE_mila_mix_template, self ).update( node )
		self.bump.update( node )

	def clearBump( self ):
		try:
			cmds.setAttr( self.attr( "bump" ), 0, 0, 0 )
		except RuntimeError:
			pass


class AE_mila_diffuse_reflection_template( AE_mila_base_template ):

	def __init__( self, node ):

		super( AE_mila_diffuse_reflection_template, self ).__init__( node )

		self.controls = []

		self.controls += AE_tint_roughness_template( node, "Diffuse Reflection", False )
		self.controls += AE_contribution_template( node )


class AE_mila_diffuse_transmission_template( AE_mila_base_template ):

	def __init__( self, node ):

		super( AE_mila_diffuse_transmission_template, self ).__init__( node )

		self.controls = []

		self.controls += AE_tint_roughness_template( node, "Diffuse Reflection", False )
		self.controls += AE_contribution_template( node )


class AE_mila_glossy_reflection_template( AE_mila_base_template ):

	def __init__( self, node ):

		super( AE_mila_glossy_reflection_template, self ).__init__( node )

		self.controls = []

		self.controls += AE_tint_roughness_template( node, "Glossy Reflection", False )
		self.controls += AE_anisotropy_template( node )
		max_dist_data = AE_max_dist_template( node )
		self.controls += max_dist_data[0]
		self.connectControls += max_dist_data[1]
		self.controls += AE_contribution_template( node )


class AE_mila_specular_reflection_template( AE_mila_base_template ):

	def __init__( self, node ):

		super( AE_mila_specular_reflection_template, self ).__init__( node )

		self.controls = []

		self.controls += AE_tint_roughness_template( node, "Specular Reflection", False )
		max_dist_data = AE_max_dist_template( node )
		self.controls += max_dist_data[0]
		self.connectControls += max_dist_data[1]
		self.controls += AE_contribution_template( node )


class AE_mila_glossy_transmission_template( AE_mila_base_template ):

	def __init__( self, node ):

		super( AE_mila_glossy_transmission_template, self ).__init__( node )

		self.controls = []

		self.controls += AE_tint_roughness_template( node, "Glossy Reflection", False )
		self.controls += AE_anisotropy_template( node )

		max_dist_data = AE_max_dist_template( node )
		self.controls += max_dist_data[0]
		self.connectControls += max_dist_data[1]

		self.controls += AE_contribution_template( node )


class AE_mila_specular_transmission_template( AE_mila_base_template ):

	def __init__( self, node ):

		super( AE_mila_specular_transmission_template, self ).__init__( node )

		self.controls = []

		self.controls += AE_tint_roughness_template( node, "Specular Transmission", False )
		max_dist_data = AE_max_dist_template( node )
		self.controls += max_dist_data[0]
		self.connectControls += max_dist_data[1]
		self.controls += AE_contribution_template( node )


class AE_mila_emission_template( AE_mila_base_template ):

	def __init__( self, node ):

		super( AE_mila_emission_template, self ).__init__( node )

		self.controls = []

		self.controls += AE_tint_roughness_template( node, "Emission", False )


class AE_mila_transparency_template( AE_mila_base_template ):

	def __init__( self, node ):

		super( AE_mila_transparency_template, self ).__init__( node )

		self.controls = []

		self.addControl( "transparency", cmds.attrColorSliderGrp( attribute=self.attr( "transparency" ), label="Transparency", columnWidth=columnWidthData ), cmds.attrColorSliderGrp )


class AE_mila_scatter_template( AE_mila_base_template ):

	def __init__( self, node ):

		super( AE_mila_scatter_template, self ).__init__( node )

		if cmds.frameLayout( label="Front Scatter", collapsable=True ):
			if cmds.columnLayout( adj=True ):
				self.addControl( "front_tint", cmds.attrColorSliderGrp( attribute=self.attr( "front_tint" ), label="Tint", columnWidth=columnWidthData ), cmds.attrColorSliderGrp )
				self.addControl( "front_weight", cmds.attrFieldSliderGrp( attribute=self.attr( "front_weight" ), label="Weight", columnWidth=columnWidthData ), cmds.attrFieldSliderGrp )
				self.addControl( "front_radius", cmds.attrFieldGrp( attribute=self.attr( "front_radius" ), label="Radius", columnWidth=columnWidthData3 ), cmds.attrFieldGrp )
				self.addControl( "front_radius_mod", cmds.attrColorSliderGrp( attribute=self.attr( "front_radius_mod" ), label="Radius Mod", columnWidth=columnWidthData ), cmds.attrColorSliderGrp )
			cmds.setParent( ".." )
		cmds.setParent( ".." )

		if cmds.frameLayout( label="Back Scatter", collapsable=True ):
			if cmds.columnLayout( adj=True ):
				self.addControl( "back_tint", cmds.attrColorSliderGrp( attribute=self.attr( "back_tint" ), label="Tint", columnWidth=columnWidthData ), cmds.attrColorSliderGrp )
				self.addControl( "back_weight", cmds.attrFieldSliderGrp( attribute=self.attr( "back_weight" ), label="Weight", columnWidth=columnWidthData ), cmds.attrFieldSliderGrp )
				self.addControl( "back_radius", cmds.attrFieldGrp( attribute=self.attr( "back_radius" ), label="Radius", columnWidth=columnWidthData3 ), cmds.attrFieldGrp )
				self.addControl( "back_radius_mod", cmds.attrColorSliderGrp( attribute=self.attr( "back_radius_mod" ), label="Radius Mod", columnWidth=columnWidthData ), cmds.attrColorSliderGrp )
				self.addControl( "back_depth", cmds.attrFieldSliderGrp( attribute=self.attr( "back_depth" ), label="Depth", columnWidth=columnWidthData ), cmds.attrFieldSliderGrp )
			cmds.setParent( ".." )
		cmds.setParent( ".." )


		if cmds.frameLayout( label="Storage And Optimization", collapsable=True ):
			if cmds.columnLayout( adj=True ):

				self.addControl( "scale_conversion", cmds.attrFieldSliderGrp( attribute=self.attr( "scale_conversion" ), label="Scale", columnWidth=columnWidthData ), cmds.attrFieldSliderGrp )
				self.addControl( "sampling_radius_mult", cmds.attrFieldSliderGrp( attribute=self.attr( "sampling_radius_mult" ), label="Sampling Factor", columnWidth=columnWidthData ), cmds.attrFieldSliderGrp )

				self.addControl( "resolution", cmds.attrEnumOptionMenuGrp( attribute=self.attr( "resolution" ), label='Resolution', columnWidth=columnWidthData3,
						   ei=[( 0, "2 x Image" ),
								 ( 1, "1 x Image" ),
								 ( 2, "1/2 x Image" ),
								 ( 3, "1/3 x Image" ),
								 ( 4, "1/4 x Image" ),
								 ( 5, "1/5 x Image" )] ),
							cmds.attrEnumOptionMenuGrp
								)

				self.addControl( "light_storage_gamma", cmds.attrFieldSliderGrp( attribute=self.attr( "light_storage_gamma" ), label="Gamma", columnWidth=columnWidthData ), cmds.attrFieldSliderGrp )
			cmds.setParent( ".." )
		cmds.setParent( ".." )

		self.controls += AE_contribution_template( node )


def AE_anisotropy_template( node, label="Anisotropy", collapse=True ):

	controls = []

	def attr( attr ):
		return "%s.%s" % ( node, attr )

	if cmds.frameLayout( label=label, collapse=collapse, collapsable=True ):
		if cmds.columnLayout( adj=True ):

			controls.append( ( "anisotropy", cmds.attrFieldSliderGrp( attribute=attr( "anisotropy" ), label="Anisotropy" , columnWidth=columnWidthData ), cmds.attrFieldSliderGrp ) )
			controls.append( ( "aniso_angle", cmds.attrFieldSliderGrp( attribute=attr( "aniso_angle" ), label="Angle", columnWidth=columnWidthData ), cmds.attrFieldSliderGrp ) )
			controls.append( ( "aniso_channel", cmds.attrFieldSliderGrp( attribute=attr( "aniso_channel" ), label="Channel", columnWidth=columnWidthData ), cmds.attrFieldSliderGrp ) )

		cmds.setParent( ".." )
	cmds.setParent( ".." )

	return controls


def AE_tint_roughness_template( node, label="Base", collapse=True ):

	controls = []

	def attr( attr ):
		return "%s.%s" % ( node, attr )

	if cmds.frameLayout( label=label, collapse=collapse, collapsable=True ):
		if cmds.columnLayout( adj=True ):

			controls.append( ( "tint", cmds.attrColorSliderGrp( attribute=attr( "tint" ), label="Tint" , columnWidth=columnWidthData ), cmds.attrColorSliderGrp ) )

			try:
				controls.append( ( "roughness", cmds.attrFieldSliderGrp( attribute=attr( "roughness" ), label="Roughness", columnWidth=columnWidthData ), cmds.attrFieldSliderGrp ) )
			except RuntimeError:
				pass

			try:
				controls.append( ( "ior", cmds.attrFieldSliderGrp( attribute=attr( "ior" ), label="IOR", columnWidth=columnWidthData ), cmds.attrFieldSliderGrp ) )
			except RuntimeError:
				pass
			try:
				controls.append( ( "intensity", cmds.attrFieldSliderGrp( attribute=attr( "intensity" ), label="Intensity", columnWidth=columnWidthData ), cmds.attrFieldSliderGrp ) )
			except RuntimeError:
				pass

		cmds.setParent( ".." )
	cmds.setParent( ".." )

	return controls


def AE_contribution_template( node, label="Contribution" , collapse=True ):

	controls = []

	def attr( attr ):
		return "%s.%s" % ( node, attr )

	if cmds.frameLayout( label=label, collapse=collapse, collapsable=True ):
		if cmds.columnLayout( adj=True ):

			controls.append( ( "direct", cmds.attrFieldSliderGrp( attribute=attr( "direct" ), label="Direct" , columnWidth=columnWidthData ), cmds.attrFieldSliderGrp ) )
			controls.append( ( "indirect", cmds.attrFieldSliderGrp( attribute=attr( "indirect" ), label="Indirect", columnWidth=columnWidthData ), cmds.attrFieldSliderGrp ) )

		cmds.setParent( ".." )
	cmds.setParent( ".." )

	return controls


def AE_max_dist_template( node, label="Max Distance", collapse=True ):
	class AE_max_dist_template_obj( object ):

		def __init__( self, node, label="Max Distance", collapse=True ):

			self.controls = []
			self.connectControls = []

			def attr( attr ):
				return "%s.%s" % ( node, attr )

			self.node = node

			if cmds.frameLayout( label=label, collapse=collapse, collapsable=True ):
				if cmds.columnLayout( adj=True ):

					self.use_max_dist = cmds.checkBoxGrp( label="", label1="Use Max Distance", columnWidth=columnWidthData , cc=self.value_changed )
					self.connectControls.append( ( "use_max_dist", self.use_max_dist, 2 ) )
					cmds.connectControl( self.use_max_dist, attr( "use_max_dist" ), index=2 )

					self.max_dist = cmds.attrFieldSliderGrp( attribute=attr( "max_dist" ), label="Max Dist", columnWidth=columnWidthData )
					self.controls.append( ( "max_dist", self.max_dist, cmds.attrFieldSliderGrp ) )

					self.use_color = cmds.checkBoxGrp( label="", label1="Use Color", columnWidth=columnWidthData , cc=self.value_changed )
					self.connectControls.append( ( "use_max_dist_color", self.use_color, 2 ) )
					cmds.connectControl( self.use_color, attr( "use_max_dist_color" ), index=2 )

					self.color = cmds.attrColorSliderGrp( attribute=attr( "max_dist_color" ), label="Color", columnWidth=columnWidthData )
					self.controls.append( ( "max_dist_color", self.color, cmds.attrColorSliderGrp ) )

				cmds.setParent( ".." )
			cmds.setParent( ".." )

			self.value_changed()


		def attr( self, attr ):
			return "%s.%s" % ( self.node, attr )

		def value_changed( self, *args ):

			value = cmds.checkBoxGrp( self.use_max_dist, q=True, value1=True )

			for control in [self.max_dist, self.use_color, self.color]:
				cmds.control( control, edit=True, enable=value )

			color_value = cmds.checkBoxGrp( self.use_color, q=True, value1=True )

			cmds.control( self.color, edit=True, enable=color_value )

	obj = AE_max_dist_template_obj( node, label, collapse )

	return obj.controls, obj.connectControls


def AE_mila_component_template( node ):

	function = "AE_%s_template" % cmds.nodeType( node )
	try:
		return globals()[function]( node )
	except KeyError:
		return ""

