# coding=utf-8
"""This module has the main GUI interaction logic for AnimationWorkbench."""

__copyright__ = "Copyright 2022, Tim Sutton"
__license__ = "GPL version 3"
__email__ = "tim@kartoza.com"
__revision__ = "$Format:%H$"

# This will make the QGIS use a world projection and then move the center
# of the CRS sequentially to create a spinning globe effect
from enum import Enum
from typing import List, Optional

# This import is to enable SIP API V2
# noinspection PyUnresolvedReferences
import qgis  # NOQA
from qgis.PyQt.QtCore import (
    pyqtSignal,
    QProcess
)
from qgis.core import (
    QgsTask,
    QgsBlockingProcess,
    QgsFeedback
)

from .utilities import get_ui_class, which

FORM_CLASS = get_ui_class("animation_workbench_base.ui")


class MovieFormat(Enum):
    GIF = 0
    MP4 = 1


class MovieCreationTask(QgsTask):
    FORMAT_GIF = "FORMAT_GIF"

    message = pyqtSignal(str)
    movie_created = pyqtSignal(str)

    def __init__(
            self,
            output_file: str,
            music_file: str,
            output_format: MovieFormat,
            work_directory: str,
            frame_filename_prefix: str,
            framerate: int,
    ):
        super().__init__("Exporting Movie", QgsTask.Flag.CanCancel)

        self.output_file = output_file
        self.music_file = music_file
        self.format = output_format
        self.work_directory = work_directory
        self.frame_filename_prefix = frame_filename_prefix
        self.framerate = framerate

        self.feedback: Optional[QgsFeedback] = None

    def run_process(self, command: str, arguments: List[str]):

        self.message.emit(f"Generating Movie: " + command + ' ' + ' '.join(arguments))

        def on_stdout(ba):
            val = ba.data().decode('UTF-8')

            on_stdout.buffer += val
            if on_stdout.buffer.endswith('\n') or on_stdout.buffer.endswith('\r'):
                # flush buffer
                self.message.emit(on_stdout.buffer.rstrip())
                on_stdout.buffer = ''

        on_stdout.progress = 0
        on_stdout.buffer = ''

        def on_stderr(ba):
            val = ba.data().decode('UTF-8')
            on_stderr.buffer += val

            if on_stderr.buffer.endswith('\n') or on_stderr.buffer.endswith('\r'):
                # flush buffer
                self.message.emit(on_stderr.buffer.rstrip())
                on_stderr.buffer = ''

        on_stderr.buffer = ''

        proc = QgsBlockingProcess(command, arguments)
        proc.setStdOutHandler(on_stdout)
        proc.setStdErrHandler(on_stderr)

        res = proc.run(self.feedback)
        if self.feedback.isCanceled() and res != 0:
            self.message.emit('Process was canceled and did not complete')
        elif not self.feedback.isCanceled() and proc.exitStatus() == QProcess.CrashExit:
            self.message.emit('Process was unexpectedly terminated')
        elif res == 0:
            self.message.emit('Process completed successfully')
        elif proc.processError() == QProcess.FailedToStart:
            self.message.emit(
                'Process {} failed to start. Either {} is missing, or you may have insufficient permissions to run the program.').format(
                command, command)
        else:
            self.message.emit('Process returned error code {}'.format(res))

    def run(self):
        """
        Creates a movie in a background task
        """

        self.feedback = QgsFeedback()

        if self.format == MovieFormat.GIF:
            self.message.emit("Generating GIF")

            convert = which("convert")[0]
            self.message.emit(f"convert found: {convert}")

            # Now generate the GIF. If this fails try to run the call from
            # the command line and check the path to convert (provided by
            # ImageMagick) is correct...
            # delay of 3.33 makes the output around 30fps

            self.run_process(convert,
                             [
                                 '-delay', str(100 / self.framerate),
                                 '-loop' ,'0',
                                 f'{self.work_directory}/{self.frame_filename_prefix}-*.png',
                                 self.output_file
                             ])

            # Now do a second pass with image magick to resize and compress the
            # gif as much as possible.  The remap option basically takes the
            # first image as a reference image for the colour palette Depending
            # on you cartography you may also want to bump up the colors param
            # to increase palette size and of course adjust the scale factor to
            # the ultimate image size you want
            self.run_process(convert,
                             [
                                 self.output_file,
                                 '-coalesce',
                                 '-scale' ,'600x600',
                                 '-fuzz', '2%', '+dither',
                                 '-remap' ,f'{self.output_file}[20]',
                                 '+dither',
                                 '-colors', '14',
                                 '-layers',
                                 'Optimize',
                                 f'{self.work_directory}/animation_small.gif'
                             ]
                             )

            self.message.emit(f"GIF written to {self.output_file}")
            self.movie_created.emit(self.output_file)
        else:
            self.message.emit("Generating MP4 Movie")
            ffmpeg = which("ffmpeg")[0]
            # Also, we will make a video of the scene - useful for cases where
            # you have a larger colour palette and gif will not hack it.
            # The Pad option is to deal with cases where ffmpeg complains
            # because the h or w of the image is an odd number of pixels.
            # color=white pads the video with white pixels.
            # Change to black if needed.
            # -y to force overwrite exising file
            self.message.emit(f"ffmpeg found: {ffmpeg}")

            arguments = [
                '-y',
                f'-framerate', str(self.framerate),
                '-pattern_type', 'glob',
                '-i', f"{self.work_directory}/{self.frame_filename_prefix}-*.png"
            ]

            if self.music_file:
                arguments.append(f"-i {self.music_file}")

            arguments.extend([
                '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2:color=white',
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                self.output_file
            ])

            # windows_command = ("""
            #    %s -y -framerate %s -pattern_type sequence \
            #    -start_number 0000000001 \
            #    -i "%s/%s-%00000000010d.png" -vf \
            #    "pad=ceil(iw/2)*2:ceil(ih/2)*2:color=white" \
            #    -c:v libx264 -pix_fmt yuv420p %s""" % (
            #    ffmpeg,
            #    framerate,
            #    self.work_directory,
            #    self.frame_filename_prefix,
            #    self.output_file))

            self.run_process(ffmpeg, arguments)
            self.message.emit(f"MP4 written to {self.output_file}")
            self.movie_created.emit(self.output_file)

        self.feedback = None
        return True

    def cancel(self):
        if self.feedback is not None:
            self.feedback.cancel()

        super().cancel()
