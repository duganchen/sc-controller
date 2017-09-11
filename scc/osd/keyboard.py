
#!/usr/bin/env python2
"""
SC-Controller - OSD Menu

Display menu that user can navigate through and print chosen item id to stdout
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, Gdk, GdkX11, GLib
from scc.constants import LEFT, RIGHT, STICK, STICK_PAD_MIN, STICK_PAD_MAX
from scc.constants import STICK_PAD_MIN_HALF, STICK_PAD_MAX_HALF
from scc.constants import SCButtons
from scc.tools import point_in_gtkrect, circle_to_square, find_profile, clamp
from scc.paths import get_share_path, get_config_path
from scc.parser import TalkingActionParser
from scc.menu_data import MenuData
from scc.actions import Action
from scc.profile import Profile
from scc.config import Config
from scc.uinput import Keys
from scc.lib import xwrappers as X
from scc.gui.daemon_manager import DaemonManager
from scc.gui.keycode_to_key import KEY_TO_KEYCODE
from scc.gui.gdk_to_key import KEY_TO_GDK
from scc.gui.svg_widget import SVGWidget
from scc.osd.timermanager import TimerManager
from scc.osd.slave_mapper import SlaveMapper
from scc.osd import OSDWindow
import scc.osd.osk_actions


import os, sys, json, logging
log = logging.getLogger("osd.keyboard")


class Keyboard(OSDWindow, TimerManager):
	EPILOG="""Exit codes:
   0  - clean exit, user closed keyboard
   1  - error, invalid arguments
   2  - error, failed to access sc-daemon, sc-daemon reported error or died while menu is displayed.
   3  - erorr, failed to lock input stick, pad or button(s)
	"""
	OSK_PROF_NAME = ".scc-osd.keyboard"
	
	def __init__(self, config=None):
		self.kbimage = os.path.join(get_config_path(), 'keyboard.svg')
		if not os.path.exists(self.kbimage):
			# Prefer image in ~/.config/scc, but load default one as fallback
			self.kbimage = os.path.join(get_share_path(), "images", 'keyboard.svg')
		self.background = None
		
		cursor = os.path.join(get_share_path(), "images", 'menu-cursor.svg')
		self.cursors = {}
		self.cursors[LEFT] = Gtk.Image.new_from_file(cursor)
		self.cursors[LEFT].set_name("osd-keyboard-cursor")
		self.cursors[RIGHT] = Gtk.Image.new_from_file(cursor)
		self.cursors[RIGHT].set_name("osd-keyboard-cursor")
		
		TimerManager.__init__(self)
		OSDWindow.__init__(self, "osd-keyboard")
		self.daemon = None
		self.config = config or Config()
		self.dpy = X.Display(hash(GdkX11.x11_get_default_xdisplay()))
		self.c = Gtk.Box()
		self.c.set_name("osd-keyboard-container")
		
		self.f = Gtk.Fixed()
	
	
	def _create_background(self):
		self.background = KeyboardArea(self.kbimage)
		self._pack()
	
	
	def _pack(self):
		self.f.add(self.background)
		self.f.add(self.cursors[LEFT])
		self.f.add(self.cursors[RIGHT])
		self.c.add(self.f)
		self.add(self.c)
	
	
	def show(self, *a):
		if self.background is None:
			self._create_background()
		OSDWindow.show(self, *a)


class KeyboardArea(Gtk.DrawingArea):
	""" DrawingArea that draws on-screen keyboard """
	
	def __init__(self, filename):
		Gtk.DrawingArea.__init__(self)
		self.filename = filename
		self.set_size_request(300, 100)
	
	
	def do_draw(self, cr):
		allocation = self.get_allocation()
		context = Gtk.Widget.get_style_context(self)
		Gtk.render_background(context, cr, 0, 0,
				allocation.width, allocation.height)
