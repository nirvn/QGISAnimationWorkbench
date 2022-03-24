# coding=utf-8
"""This module has the main GUI interaction logic for AnimationWorkbench."""

__copyright__ = "Copyright 2022, Tim Sutton"
__license__ = "GPL version 3"
__email__ = "tim@kartoza.com"
__revision__ = '$Format:%H$'

# This will make the QGIS use a world projection and then move the center
# of the CRS sequentially to create a spinning globe effect
import os
import tempfile

# This import is to enable SIP API V2
# noinspection PyUnresolvedReferences
import qgis  # NOQA
from PyQt5.QtMultimedia import (
    QMediaContent,
    QMediaPlayer)
from PyQt5.QtMultimediaWidgets import QVideoWidget
from qgis.PyQt.QtCore import (
    pyqtSlot,
    QUrl)
from qgis.PyQt.QtGui import (
    QIcon,
    QPixmap,
    QImage)
from qgis.PyQt.QtWidgets import (
    QStyle,
    QFileDialog,
    QDialog,
    QDialogButtonBox,
    QGridLayout)
from qgis.core import (
    QgsPointXY,
    QgsExpressionContextUtils,
    QgsProject,
    QgsMapLayerProxyModel,
    QgsReferencedRectangle
)

from .settings import set_setting, setting
from .utilities import get_ui_class, which, resources_path
from .animation_controller import (
    MapMode,
    AnimationController,
    InvalidAnimationParametersException
)

FORM_CLASS = get_ui_class('animation_workbench_base.ui')


class AnimationWorkbench(QDialog, FORM_CLASS):
    """Dialog implementation class Animation Workbench class."""

    def __init__(self, parent=None, iface=None, render_queue=None):
        """Constructor for the workbench dialog.

        :param parent: Parent widget of this dialog.
        :type parent: QWidget

        :param iface: QGIS Plugin Interface.
        :type iface: QgsInterface

        :param render_queue: Render queue to processing each frame.
        :type render_queue: RenderQueue
        """
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.render_queue = render_queue
        self.setWindowTitle(self.tr('Animation Workbench'))
        icon = resources_path(
            'img', 'icons', 'animation-workshop.svg')
        self.setWindowIcon(QIcon(icon))
        self.parent = parent
        self.iface = iface

        self.extent_group_box.setMapCanvas(self.iface.mapCanvas())
        self.scale_range.setMapCanvas(self.iface.mapCanvas())

        self.output_log_text_edit.append(
            'Welcome to the QGIS Animation Workbench')
        self.output_log_text_edit.append(
            '© Tim Sutton, Feb 2022')

        ok_button = self.button_box.button(QDialogButtonBox.Ok)
        # ok_button.clicked.connect(self.accept)
        ok_button.setText('Run')
        ok_button.setEnabled(False)

        # place where working files are stored
        self.work_directory = tempfile.gettempdir()
        self.frame_filename_prefix = 'animation_workbench'
        # place where final products are stored
        output_file = setting(key='output_file', default='', prefer_project_setting=True)
        if output_file:
            self.movie_file_edit.setText(output_file)
            ok_button.setEnabled(True)

        self.movie_file_button.clicked.connect(
            self.set_output_name)

        music_file = setting(key='music_file', default='', prefer_project_setting=True)
        if music_file:
            self.music_file_edit.setText(music_file)
        self.music_file_button.clicked.connect(
            self.choose_music_file)

        # Work around for not being able to set the layer
        # types allowed in the QgsMapLayerSelector combo
        # See https://github.com/qgis/QGIS/issues/38472#issuecomment-715178025
        self.layer_combo.setFilters(
            QgsMapLayerProxyModel.PointLayer |
            QgsMapLayerProxyModel.LineLayer |
            QgsMapLayerProxyModel.PolygonLayer)

        prev_layer_id, ok = QgsProject.instance().readEntry('animation', 'layer_id')
        if prev_layer_id:
            layer = QgsProject.instance().mapLayer(prev_layer_id)
            if layer:
                self.layer_combo.setLayer(layer)

        self.extent_group_box.setOutputCrs(
            QgsProject.instance().crs()
        )
        self.extent_group_box.setOutputExtentFromUser(
            self.iface.mapCanvas().extent(),
            QgsProject.instance().crs())
        # self.extent_group_box.setOriginalExtnt()
        # Set up things for context help
        self.help_button = self.button_box.button(
            QDialogButtonBox.Help)
        # Allow toggling the help button
        self.help_button.setCheckable(True)
        self.help_button.toggled.connect(self.help_toggled)

        # Close button action
        self.button_box.rejected.connect(self.reject)
        self.button_box.accepted.connect(self.accept)
        # Fix ends

        # Used by ffmpeg and convert to set the fps for rendered videos
        self.framerate_spin.setValue(int(
            setting(key='frames_per_second', default='90', prefer_project_setting=True)))
        # How many frames to render for each feature pair transition
        # The output is generated at e.g. 30fps so choosing 30
        # would fly to each feature for 1s
        # You can then use the 'current_feature' project variable
        # to determine the current feature id
        # and the 'feature_frame' project variable to determine
        # the frame number for the current feature based on frames_for_interval

        self.feature_frames_spin.setValue(int(
            setting(key='frames_per_feature', default='90', prefer_project_setting=True)))

        # How many frames to dwell at each feature for (output at e.g. 30fps)
        self.hover_frames_spin.setValue(int(
            setting(key='dwell_frames', default='30', prefer_project_setting=True)))
        # How many frames to render when we are in static mode
        self.extent_frames_spin.setValue(int(
            setting(key='frames_for_extent', default='90', prefer_project_setting=True)))
        # Keep the scales the same if you dont want it to zoom in an out
        self.scale_range.setMaximumScale(float(setting(key='max_scale', default='10000000', prefer_project_setting=True)))
        self.scale_range.setMinimumScale(float(setting(key='min_scale', default='25000000', prefer_project_setting=True)))

        self.last_preview_image = None

        # Note: self.pan_easing_widget and zoom_easing_preview are
        # custom widgets implemented in easing_preview.py
        # and added in designer as promoted widgets.
        self.pan_easing_widget.set_checkbox_label('Enable Pan Easing')
        pan_easing_name = setting(key='pan_easing', default='Linear', prefer_project_setting=True)
        self.pan_easing_widget.set_preview_color('#00ff00')
        self.pan_easing_widget.set_easing_by_name(pan_easing_name)
        if setting(key='enable_pan_easing', default='false', prefer_project_setting=True).lower() == 'false':
            self.pan_easing_widget.disable()
        else:
            self.pan_easing_widget.enable()
        self.pan_easing = self.pan_easing_widget.get_easing()
        self.pan_easing_widget.easing_changed_signal.connect(
            self.pan_easing_changed
        )

        self.zoom_easing_widget.set_checkbox_label('Enable Zoom Easing')
        zoom_easing_name = setting(key='zoom_easing', default='Linear', prefer_project_setting=True)
        self.zoom_easing_widget.set_preview_color('#0000ff')
        self.zoom_easing_widget.set_easing_by_name(zoom_easing_name)
        if setting(key='enable_zoom_easing', default='false', prefer_project_setting=True).lower() == 'false':
            self.zoom_easing_widget.disable()
        else:
            self.zoom_easing_widget.enable()

        self.zoom_easing = self.zoom_easing_widget.get_easing()
        self.zoom_easing_widget.easing_changed_signal.connect(
            self.zoom_easing_changed
        )

        QgsExpressionContextUtils.setProjectVariable(
            QgsProject.instance(), 'frames_per_feature', 0)
        QgsExpressionContextUtils.setProjectVariable(
            QgsProject.instance(), 'current_frame_for_feature', 0)
        QgsExpressionContextUtils.setProjectVariable(
            QgsProject.instance(), 'current_feature_id', 0)
        # None, Panning, Hovering
        QgsExpressionContextUtils.setProjectVariable(
            QgsProject.instance(), 'current_animation_action', 'None')

        QgsExpressionContextUtils.setProjectVariable(
            QgsProject.instance(), 'current_frame', 'None')
        QgsExpressionContextUtils.setProjectVariable(
            QgsProject.instance(), 'total_frame_count', 'None')

        self.map_mode = None
        mode_string = setting(key='map_mode', default='sphere', prefer_project_setting=True)
        if mode_string == 'sphere':
            self.map_mode == MapMode.SPHERE
            self.radio_sphere.setChecked(True)
            self.status_stack.setCurrentIndex(0)
            self.settings_stack.setCurrentIndex(0)
        elif mode_string == 'planar':
            self.map_mode == MapMode.PLANAR
            self.radio_planar.setChecked(True)
            self.status_stack.setCurrentIndex(0)
            self.settings_stack.setCurrentIndex(0)
        else:
            self.map_mode == MapMode.FIXED_EXTENT
            self.radio_extent.setChecked(True)
            self.status_stack.setCurrentIndex(1)
            self.settings_stack.setCurrentIndex(1)

        self.radio_planar.toggled.connect(
            self.show_non_fixed_extent_settings
        )
        self.radio_sphere.toggled.connect(
            self.show_non_fixed_extent_settings
        )
        self.radio_extent.toggled.connect(
            self.show_fixed_extent_settings
        )

        # Set an initial image in the preview based on the current map
        image = self.render_queue.render_image()
        if not image.isNull():
            pixmap = QPixmap.fromImage(image)
            self.current_frame_preview.setPixmap(pixmap)

        self.progress_bar.setValue(0)

        reuse_cache = setting(key='reuse_cache', default='false')
        if reuse_cache == 'false':
            self.reuse_cache.setChecked(False)
        else:
            self.reuse_cache.setChecked(True)

        # Video playback stuff - see bottom of file for related methods
        self.media_player = QMediaPlayer(
            None,  # .video_preview_widget,
            QMediaPlayer.VideoSurface)
        video_widget = QVideoWidget()
        # self.video_page.replaceWidget(self.video_preview_widget,video_widget)
        self.play_button.setIcon(
            self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_button.clicked.connect(self.play)
        self.media_player.setVideoOutput(video_widget)
        self.media_player.stateChanged.connect(self.media_state_changed)
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.media_player.error.connect(self.handle_video_error)
        layout = QGridLayout(self.video_preview_widget)
        layout.addWidget(video_widget)
        # Enable image preview page on startup
        self.preview_stack.setCurrentIndex(0)
        # Enable easing status page on startup
        self.status_stack.setCurrentIndex(0)
        self.render_queue.status_changed.connect(
            self.show_status)
        self.render_queue.processing_completed.connect(
            self.processing_completed)
        self.render_queue.status_message.connect(
            self.show_message)
        self.render_queue.image_rendered.connect(
            self.load_image)

    def closeEvent(self, event):
        self.save_state()
        self.reject()

    def show_message(self, message):
        self.output_log_text_edit.append(message)

    # slot
    def pan_easing_changed(self, easing):
        self.output_log_text_edit.append(
            'Pan easing set to: %s' %
            self.pan_easing_widget.easing_name())
        self.pan_easing = easing

    # slot
    def zoom_easing_changed(self, easing):
        self.output_log_text_edit.append(
            'Zoom easing set to: %s' %
            self.pan_easing_widget.easing_name())
        self.zoom_easing = easing

    def show_non_fixed_extent_settings(self):

        self.settings_stack.setCurrentIndex(0)

    def show_fixed_extent_settings(self):

        self.settings_stack.setCurrentIndex(1)

    def show_status(self):
        """
        Display the size of the QgsTaskManager queue.

        :returns: None
        """
        self.active_lcd.display(
            self.render_queue.active_queue_size)
        self.total_tasks_lcd.display(
            self.render_queue.total_queue_size
        )
        self.remaining_features_lcd.display(
            self.render_queue.total_feature_count -
            self.render_queue.completed_feature_count)
        self.completed_tasks_lcd.display(
            self.render_queue.total_completed
        )
        self.completed_features_lcd.display(
            self.render_queue.completed_feature_count)

    def set_output_name(self):
        # Popup a dialog to request the filename if scenario_file_path = None
        dialog_title = 'Save video'
        ok_button = self.button_box.button(QDialogButtonBox.Ok)
        ok_button.setText('Run')
        ok_button.setEnabled(False)

        output_directory = os.path.dirname(self.movie_file_edit.text())
        if not output_directory:
            output_directory = self.work_directory

        # noinspection PyCallByClass,PyTypeChecker
        file_path, __ = QFileDialog.getSaveFileName(
            self,
            dialog_title,
            os.path.join(output_directory, 'qgis_animation.mp4'),
            "Video (*.mp4);;GIF (*.gif)")
        if file_path is None or file_path == '':
            ok_button.setEnabled(False)
            return
        ok_button.setEnabled(True)
        self.movie_file_edit.setText(file_path)

    def choose_music_file(self):
        # Popup a dialog to request the filename for music backing track
        dialog_title = 'Music for video'

        # noinspection PyCallByClass,PyTypeChecker
        file_path, __ = QFileDialog.getOpenFileName(
            self,
            dialog_title,
            self.music_file_edit.text(),
            "Mp3 (*.mp3);;Wav (*.wav)")
        if file_path is None or file_path == '':
            return
        self.music_file_edit.setText(self.music_file)

    def save_state(self):
        """
        We save some project settings to both QSettings AND the current project, others just to the current project,
        others just to settings...
        """
        set_setting(key='frames_per_second', value=self.framerate_spin.value(), store_in_project=True)

        if self.radio_sphere.isChecked():
            set_setting(key='map_mode', value='sphere', store_in_project=True)
        elif self.radio_planar.isChecked():
            set_setting(key='map_mode', value='planar', store_in_project=True)
        else:
            set_setting(key='map_mode', value='fixed_extent', store_in_project=True)
        # Save state
        set_setting(key='frames_per_feature', value=self.feature_frames_spin.value(), store_in_project=True)
        set_setting(key='dwell_frames', value=self.hover_frames_spin.value(), store_in_project=True)
        set_setting(key='frames_for_extent', value=self.extent_frames_spin.value(), store_in_project=True)
        set_setting(key='max_scale', value=self.scale_range.maximumScale(), store_in_project=True)
        set_setting(key='min_scale', value=self.scale_range.minimumScale(), store_in_project=True)
        set_setting(
            key='enable_pan_easing',
            value=self.pan_easing_widget.is_enabled(), store_in_project=True)
        set_setting(
            key='enable_zoom_easing',
            value=self.zoom_easing_widget.is_enabled(), store_in_project=True)
        set_setting(
            key='pan_easing',
            value=self.pan_easing_widget.easing_name(), store_in_project=True)
        set_setting(
            key='zoom_easing',
            value=self.zoom_easing_widget.easing_name(), store_in_project=True)
        set_setting(key='reuse_cache', value=self.reuse_cache.isChecked())
        set_setting(key='output_file', value=self.movie_file_edit.text(), store_in_project=True)
        set_setting(key='music_file', value=self.music_file_edit.text(), store_in_project=True)

        # only saved to project
        if self.layer_combo.currentLayer():
            QgsProject.instance().writeEntry('animation', 'layer_id', self.layer_combo.currentLayer().id())
        else:
            QgsProject.instance().removeEntry('animation', 'layer_id')

    # Prevent the slot being called twize
    @pyqtSlot()
    def accept(self):
        """Process the animation sequence.

        .. note:: This is called on OK click.
        """
        # Image preview page
        self.preview_stack.setCurrentIndex(0)
        # Enable queue status page
        self.status_stack.setCurrentIndex(1)
        # set parameter from dialog

        if not self.reuse_cache.isChecked():
            os.system('rm %s/%s*' %
                      (
                          self.work_directory,
                          self.frame_filename_prefix
                      ))

        if self.radio_sphere.isChecked():
            self.map_mode = MapMode.SPHERE
        elif self.radio_planar.isChecked():
            self.map_mode = MapMode.PLANAR
        else:
            self.map_mode = MapMode.FIXED_EXTENT

        if self.map_mode != MapMode.FIXED_EXTENT:
            layer_type = qgis.core.QgsWkbTypes.displayString(
                int(self.layer_combo.currentLayer().wkbType()))
            layer_name = self.layer_combo.currentLayer().name()
            self.output_log_text_edit.append(
                'Generating flight path for %s layer: %s' %
                (layer_type, layer_name))

        self.save_state()

        self.render_queue.reset()
        self.last_preview_image = None

        self.render_queue.set_annotations(QgsProject.instance().annotationManager().annotations())
        self.render_queue.set_decorations(self.iface.activeDecorations())

        if self.map_mode == MapMode.FIXED_EXTENT:
            controller = AnimationController.create_fixed_extent_controller(
                map_settings=self.iface.mapCanvas().mapSettings(),
                output_extent=QgsReferencedRectangle(self.extent_group_box.outputExtent(),
                                                     self.extent_group_box.outputCrs()),
                total_frames=self.extent_frames_spin.value()
            )
        else:
            try:
                controller = AnimationController.create_moving_extent_controller(
                    map_settings=self.iface.mapCanvas().mapSettings(),
                    mode=self.map_mode,
                    feature_layer=self.layer_combo.currentLayer(),
                    travel_frames=self.feature_frames_spin.value(),
                    dwell_frames=self.hover_frames_spin.value(),
                    min_scale=self.scale_range.minimumScale(),
                    max_scale=self.scale_range.maximumScale(),
                    pan_easing=self.pan_easing if self.pan_easing_widget.is_enabled() else None,
                    zoom_easing=self.zoom_easing if self.zoom_easing_widget.is_enabled() else None
                )
            except InvalidAnimationParametersException as e:
                self.output_log_text_edit.append(f'Processing halted: {e}')
                return

        controller.reuse_cache = self.reuse_cache.isChecked()

        self.output_log_text_edit.append(
            'Generating {} frames'.format(controller.total_frame_count))
        self.progress_bar.setMaximum(controller.total_frame_count)
        self.progress_bar.setValue(0)

        def log_message(message):
            self.output_log_text_edit.append(message)

        controller.normal_message.connect(log_message)
        if int(setting(key='verbose_mode', default=0)):
            controller.verbose_message.connect(log_message)

        for image_counter, job in enumerate(controller.create_jobs()):
            self.output_log_text_edit.append(job.file_name)
            self.render_queue.add_job(job)
            self.progress_bar.setValue(image_counter)

        # Now all the tasks are prepared, start the render_queue processing
        self.render_queue.process_more_tasks()

    def processing_completed(self):
        """Run after all processing is done to generate gif or mp4.

        .. note:: This called by process_more_tasks when all tasks are complete.
        """

        output_file = self.movie_file_edit.text()
        music_file = self.music_file_edit.text()

        if self.radio_gif.isChecked():
            self.output_log_text_edit.append('Generating GIF')
            convert = which('convert')[0]
            self.output_log_text_edit.append('convert found: %s' % convert)
            # Now generate the GIF. If this fails try run the call from
            # the command line and check the path to convert (provided by
            # ImageMagick) is correct...
            # delay of 3.33 makes the output around 30fps
            os.system('%s -delay 3.33 -loop 0 %s/$s-*.png %s' % (
                self.work_directory,
                self.frame_filename_prefix,
                convert, self.work_directory, output_file))
            # Now do a second pass with image magick to resize and compress the
            # gif as much as possible.  The remap option basically takes the
            # first image as a reference image for the colour palette Depending
            # on you cartography you may also want to bump up the colors param
            # to increase palette size and of course adjust the scale factor to
            # the ultimate image size you want
            os.system("""
                %s %s -coalesce -scale 600x600 -fuzz 2% +dither \
                    -remap %s/%s.gif[20] +dither -colors 14 -layers \
                    Optimize %s/animation_small.gif""" % (
                convert,
                output_file,
                self.work_directory,
                self.frame_filename_prefix,
                self.work_directory
            ))
            # Video preview page
            self.preview_stack.setCurrentIndex(1)
            self.media_player.setMedia(
                QMediaContent(QUrl.fromLocalFile('/tmp/animation_small-gif')))
            self.play_button.setEnabled(True)
            self.play()
            self.output_log_text_edit.append(
                'GIF written to %s' % output_file)
        else:
            self.output_log_text_edit.append('Generating MP4 Movie')
            ffmpeg = which('ffmpeg')[0]
            # Also we will make a video of the scene - useful for cases where
            # you have a larger colour pallette and gif will not hack it.
            # The Pad option is to deal with cases where ffmpeg complains
            # because the h or w of the image is an odd number of pixels.
            # :color=white pads the video with white pixels.
            # Change to black if needed.
            # -y to force overwrite exising file
            self.output_log_text_edit.append('ffmpeg found: %s' % ffmpeg)

            framerate = str(self.framerate_spin.value())
            if music_file:
                mp3_flag = '-i %s' % music_file
            else:
                mp3_flag = ''
            unix_command = ("""
                %s -y -framerate %s -pattern_type glob \
                -i "%s/%s-*.png" %s -vf \
                "pad=ceil(iw/2)*2:ceil(ih/2)*2:color=white" \
                -c:v libx264 -pix_fmt yuv420p %s""" % (
                ffmpeg,
                framerate,
                self.work_directory,
                self.frame_filename_prefix,
                mp3_flag,
                output_file))

            # windows_command = ("""
            #    %s -y -framerate %s -pattern_type sequence -start_number 0000000001 \
            #    -i "%s/%s-%00000000010d.png" -vf \
            #    "pad=ceil(iw/2)*2:ceil(ih/2)*2:color=white" \
            #    -c:v libx264 -pix_fmt yuv420p %s""" % (
            #    ffmpeg,
            #    framerate,
            #    self.work_directory,
            #    self.frame_filename_prefix,
            #    self.output_file))

            self.output_log_text_edit.append('Generating Movie:\n%s' % unix_command)
            os.system(unix_command)
            # Video preview page
            self.preview_stack.setCurrentIndex(1)
            self.media_player.setMedia(
                QMediaContent(QUrl.fromLocalFile(output_file)))
            self.play_button.setEnabled(True)
            self.play()
            self.output_log_text_edit.append(
                'MP4 written to %s' % output_file)

    def load_image(self, name):
        if self.last_preview_image is not None and self.last_preview_image > name:
            # Images won't necessarily be rendered in order, so only update the
            # preview image if the rendered image is from later in the animation
            # vs the one we are currently showing. Avoids the preview jumping
            # forward and backward and zooming/in out in unpredictable patterns
            return

        self.last_preview_image = name
        # Load the preview with the named image file
        with open(name, 'rb') as image_file:
            content = image_file.read()
            image = QImage()
            image.loadFromData(content)
            pixmap = QPixmap.fromImage(image)
            self.current_frame_preview.setPixmap(pixmap)

    def help_toggled(self, flag):
        """Show or hide the help tab in the stacked widget.
        :param flag: Flag indicating whether help should be shown or hidden.
        :type flag: bool
        """
        if flag:
            self.help_button.setText(self.tr('Hide Help'))
            self.show_help()
        else:
            self.help_button.setText(self.tr('Show Help'))
            self.hide_help()

    def hide_help(self):
        """Hide the usage info from the user."""
        self.main_stacked_widget.setCurrentIndex(1)

    def show_help(self):
        """Show usage info to the user."""
        # Read the header and footer html snippets
        self.main_stacked_widget.setCurrentIndex(0)
        header = html_header()
        footer = html_footer()

        string = header

        message = workbench_help()

        string += message.to_html()
        string += footer

        self.help_web_view.setHtml(string)

    # Video Playback Methods
    def play(self):
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def media_state_changed(self, state):
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.play_button.setIcon(
                self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.play_button.setIcon(
                self.style().standardIcon(QStyle.SP_MediaPlay))

    def position_changed(self, position):
        self.video_slider.setValue(position)

    def duration_changed(self, duration):
        self.video_slider.setRange(0, duration)

    def set_position(self, position):
        self.media_player.setPosition(position)

    def handle_video_error(self):
        self.play_button.setEnabled(False)
        self.output_log_text_edit.append(
            self.media_player.errorString())
