# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/home/timlinux/dev/python/QGISAnimationWorkbench/ui/animation_workbench_base.ui'
#
# Created by: PyQt5 UI code generator 5.15.6
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_animation_workbench_base(object):
    def setupUi(self, animation_workbench_base):
        animation_workbench_base.setObjectName("animation_workbench_base")
        animation_workbench_base.resize(494, 779)
        self.gridLayout_3 = QtWidgets.QGridLayout(animation_workbench_base)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.button_box = QtWidgets.QDialogButtonBox(animation_workbench_base)
        self.button_box.setOrientation(QtCore.Qt.Horizontal)
        self.button_box.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Help|QtWidgets.QDialogButtonBox.Ok)
        self.button_box.setObjectName("button_box")
        self.gridLayout_3.addWidget(self.button_box, 1, 0, 1, 1)
        self.scrollArea = QtWidgets.QScrollArea(animation_workbench_base)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 478, 721))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.gridLayout_7 = QtWidgets.QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_7.setObjectName("gridLayout_7")
        self.animation_reference_group = QtWidgets.QGroupBox(self.scrollAreaWidgetContents)
        self.animation_reference_group.setObjectName("animation_reference_group")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.animation_reference_group)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.layer_combo = gui.QgsMapLayerComboBox(self.animation_reference_group)
        self.layer_combo.setObjectName("layer_combo")
        self.gridLayout_4.addWidget(self.layer_combo, 1, 1, 1, 1)
        self.point_layer_label = QtWidgets.QLabel(self.animation_reference_group)
        self.point_layer_label.setObjectName("point_layer_label")
        self.gridLayout_4.addWidget(self.point_layer_label, 1, 0, 1, 1)
        self.gridLayout_7.addWidget(self.animation_reference_group, 0, 0, 1, 1)
        self.easings_group = QtWidgets.QGroupBox(self.scrollAreaWidgetContents)
        self.easings_group.setObjectName("easings_group")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.easings_group)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.fly_easing_label = QtWidgets.QLabel(self.easings_group)
        self.fly_easing_label.setObjectName("fly_easing_label")
        self.gridLayout_2.addWidget(self.fly_easing_label, 0, 0, 1, 1)
        self.fly_easing_combo = QtWidgets.QComboBox(self.easings_group)
        self.fly_easing_combo.setObjectName("fly_easing_combo")
        self.gridLayout_2.addWidget(self.fly_easing_combo, 0, 1, 1, 1)
        self.zoom_easing_combo = QtWidgets.QComboBox(self.easings_group)
        self.zoom_easing_combo.setObjectName("zoom_easing_combo")
        self.gridLayout_2.addWidget(self.zoom_easing_combo, 1, 1, 1, 1)
        self.zoom_easing_label = QtWidgets.QLabel(self.easings_group)
        self.zoom_easing_label.setObjectName("zoom_easing_label")
        self.gridLayout_2.addWidget(self.zoom_easing_label, 1, 0, 1, 1)
        self.gridLayout_7.addWidget(self.easings_group, 2, 0, 1, 1)
        self.render_mode_group = QtWidgets.QGroupBox(self.scrollAreaWidgetContents)
        self.render_mode_group.setObjectName("render_mode_group")
        self.gridLayout = QtWidgets.QGridLayout(self.render_mode_group)
        self.gridLayout.setObjectName("gridLayout")
        self.radio_static = QtWidgets.QRadioButton(self.render_mode_group)
        self.radio_static.setObjectName("radio_static")
        self.gridLayout.addWidget(self.radio_static, 2, 0, 1, 1)
        self.radio_planar = QtWidgets.QRadioButton(self.render_mode_group)
        self.radio_planar.setObjectName("radio_planar")
        self.gridLayout.addWidget(self.radio_planar, 1, 0, 1, 1)
        self.radio_sphere = QtWidgets.QRadioButton(self.render_mode_group)
        self.radio_sphere.setObjectName("radio_sphere")
        self.gridLayout.addWidget(self.radio_sphere, 0, 0, 1, 1)
        self.gridLayout_7.addWidget(self.render_mode_group, 1, 0, 1, 1)
        self.output_destination_group = QtWidgets.QGroupBox(self.scrollAreaWidgetContents)
        self.output_destination_group.setObjectName("output_destination_group")
        self.gridLayout_6 = QtWidgets.QGridLayout(self.output_destination_group)
        self.gridLayout_6.setObjectName("gridLayout_6")
        self.folder_label = QtWidgets.QLabel(self.output_destination_group)
        self.folder_label.setObjectName("folder_label")
        self.gridLayout_6.addWidget(self.folder_label, 0, 0, 1, 1)
        self.folder_edit = QtWidgets.QLineEdit(self.output_destination_group)
        self.folder_edit.setObjectName("folder_edit")
        self.gridLayout_6.addWidget(self.folder_edit, 0, 1, 1, 1)
        self.folder_button = QtWidgets.QToolButton(self.output_destination_group)
        self.folder_button.setObjectName("folder_button")
        self.gridLayout_6.addWidget(self.folder_button, 0, 2, 1, 1)
        self.gridLayout_7.addWidget(self.output_destination_group, 5, 0, 1, 1)
        self.animation_frames_group = QtWidgets.QGroupBox(self.scrollAreaWidgetContents)
        self.animation_frames_group.setObjectName("animation_frames_group")
        self.gridLayout_8 = QtWidgets.QGridLayout(self.animation_frames_group)
        self.gridLayout_8.setObjectName("gridLayout_8")
        self.hover_frames_label = QtWidgets.QLabel(self.animation_frames_group)
        self.hover_frames_label.setObjectName("hover_frames_label")
        self.gridLayout_8.addWidget(self.hover_frames_label, 1, 0, 1, 1)
        self.hover_frames_spin = QtWidgets.QSpinBox(self.animation_frames_group)
        self.hover_frames_spin.setObjectName("hover_frames_spin")
        self.gridLayout_8.addWidget(self.hover_frames_spin, 1, 1, 1, 1)
        self.point_frames_label = QtWidgets.QLabel(self.animation_frames_group)
        self.point_frames_label.setObjectName("point_frames_label")
        self.gridLayout_8.addWidget(self.point_frames_label, 0, 0, 1, 1)
        self.point_frames_spin = QtWidgets.QSpinBox(self.animation_frames_group)
        self.point_frames_spin.setObjectName("point_frames_spin")
        self.gridLayout_8.addWidget(self.point_frames_spin, 0, 1, 1, 1)
        self.gridLayout_7.addWidget(self.animation_frames_group, 3, 0, 1, 1)
        self.output_options_group = QtWidgets.QGroupBox(self.scrollAreaWidgetContents)
        self.output_options_group.setObjectName("output_options_group")
        self.gridLayout_5 = QtWidgets.QGridLayout(self.output_options_group)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.radio_gif = QtWidgets.QRadioButton(self.output_options_group)
        self.radio_gif.setObjectName("radio_gif")
        self.gridLayout_5.addWidget(self.radio_gif, 0, 0, 1, 1)
        self.rad_movie = QtWidgets.QRadioButton(self.output_options_group)
        self.rad_movie.setObjectName("rad_movie")
        self.gridLayout_5.addWidget(self.rad_movie, 1, 0, 1, 1)
        self.gridLayout_7.addWidget(self.output_options_group, 4, 0, 1, 1)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.gridLayout_3.addWidget(self.scrollArea, 0, 0, 1, 1)

        self.retranslateUi(animation_workbench_base)
        self.button_box.accepted.connect(animation_workbench_base.accept) # type: ignore
        self.button_box.rejected.connect(animation_workbench_base.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(animation_workbench_base)

    def retranslateUi(self, animation_workbench_base):
        _translate = QtCore.QCoreApplication.translate
        animation_workbench_base.setWindowTitle(_translate("animation_workbench_base", "Dialog"))
        self.animation_reference_group.setTitle(_translate("animation_workbench_base", "Animation Reference"))
        self.point_layer_label.setText(_translate("animation_workbench_base", "Point layer"))
        self.easings_group.setTitle(_translate("animation_workbench_base", "Easings"))
        self.fly_easing_label.setText(_translate("animation_workbench_base", "Fly Easing"))
        self.fly_easing_combo.setToolTip(_translate("animation_workbench_base", "The fly easing will determine the motion \n"
"characteristics of the camera on the Y axis \n"
"as it flies across the scene."))
        self.zoom_easing_combo.setToolTip(_translate("animation_workbench_base", "The zoom easing will affect the behaviour \n"
"of the camera during zoom transitions."))
        self.zoom_easing_label.setText(_translate("animation_workbench_base", "Zoom Easing"))
        self.render_mode_group.setToolTip(_translate("animation_workbench_base", "The render mode determines the behaviour and type of the animation. \n"
"For \'Sphere\' the coordinate reference system (CRS) will \n"
"be manipulated to create a spinning globe effect. \n"
"For \'Plane\', the CRS will not be altered, but will pan and \n"
"zoom to each point. For \'Static\' the animation will not \n"
"not pan / zoom the map."))
        self.render_mode_group.setTitle(_translate("animation_workbench_base", "Render Mode"))
        self.radio_static.setText(_translate("animation_workbench_base", "Static"))
        self.radio_planar.setText(_translate("animation_workbench_base", "Planar"))
        self.radio_sphere.setText(_translate("animation_workbench_base", "Sphere"))
        self.output_destination_group.setTitle(_translate("animation_workbench_base", "Output Destination"))
        self.folder_label.setText(_translate("animation_workbench_base", "Folder"))
        self.folder_edit.setToolTip(_translate("animation_workbench_base", "The output folder will be populated with \n"
"all of the frames of the animation, and \n"
"the GIF or MP4 as selected above."))
        self.folder_button.setText(_translate("animation_workbench_base", "..."))
        self.animation_frames_group.setTitle(_translate("animation_workbench_base", "Animation Frames"))
        self.hover_frames_label.setText(_translate("animation_workbench_base", "Hover frames at each point"))
        self.hover_frames_spin.setToolTip(_translate("animation_workbench_base", "This is the number of frames that will \n"
"be used during animation of the motion from \n"
"one point to the next. Video generation \n"
"is done at 30 frames per second, so a value \n"
"of 30 here would result in a 1 second flight time \n"
"between two consecutive points."))
        self.point_frames_label.setText(_translate("animation_workbench_base", "Frames between points"))
        self.point_frames_spin.setToolTip(_translate("animation_workbench_base", "This is the number of frames that will be used during\n"
" animation of the dwell period at each point. \n"
"Video generation is done at 30 frames per \n"
"second, so a value of 30 here would result in a 1 second \n"
"dwell time."))
        self.output_options_group.setToolTip(_translate("animation_workbench_base", "Select which output format you would like. \n"
"Regardless of which you choose, a folder \n"
"of images will be created, one image per frame. \n"
"For the GIF export to work, you will \n"
"need to have the ImageMagick \'convert\'  application \n"
"available on your system. For the MP4 option to work, \n"
"you need to have the \'ffmpeg\' application on \n"
"your system."))
        self.output_options_group.setTitle(_translate("animation_workbench_base", "Output Options"))
        self.radio_gif.setText(_translate("animation_workbench_base", "Animated GIF"))
        self.rad_movie.setText(_translate("animation_workbench_base", "Movie (MP4)"))
from qgis import gui
