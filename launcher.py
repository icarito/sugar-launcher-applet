#!/usr/bin/python3
import os
import dbus
import gi
gi.require_version('Gtk', '3.0')

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

from gi.repository import Gtk
from random import randint

import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

from sugar3.bundle.activitybundle import ActivityBundle
from sugar3.graphics.menuitem import MenuItem
from sugar3.graphics import style
from sugar3.graphics import xocolor

from sugar3.datastore import datastore

from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)

from jarabe.model import shell
shell.get_model()

try:
    activities_path = os.environ['SUGAR_ACTIVITIES_PATH']
except KeyError:
    activities_path = os.path.join(os.path.expanduser("~"), "Activities")
os.environ['SUGAR_MIME_DEFAULTS'] = '/usr/share/sugar/data/mime.defaults'
os.environ['SUGAR_ACTIVITIES_HIDDEN'] = '/usr/share/sugar/data/activities.hidden'

sugar_theme = 'sugar-72'
if 'SUGAR_SCALING' in os.environ:
    if os.environ['SUGAR_SCALING'] == '100':
        sugar_theme = 'sugar-100'

# This code can be removed when we grow an xsettings daemon (the GTK+
# init routines will then automatically figure out the font settings)
settings = Gtk.Settings.get_default()
settings.set_property('gtk-theme-name', sugar_theme)
settings.set_property('gtk-icon-theme-name', 'sugar')
settings.set_property('gtk-font-name',
                      '%s %f' % (style.FONT_FACE, style.FONT_SIZE))

DS_DBUS_SERVICE = 'org.laptop.sugar.DataStore'
DS_DBUS_INTERFACE = 'org.laptop.sugar.DataStore'
DS_DBUS_PATH = '/org/laptop/sugar/DataStore'

from jarabe import apisocket
apisocket.start()

_datastore = None
def _get_datastore():
    global _datastore
    if _datastore is None:
        bus = dbus.SessionBus()
        remote_object = bus.get_object(DS_DBUS_SERVICE, DS_DBUS_PATH)
        _datastore = dbus.Interface(remote_object, DS_DBUS_INTERFACE)

        #_datastore.connect_to_signal('Created', _datastore_created_cb)
        #_datastore.connect_to_signal('Updated', _datastore_updated_cb)
        #_datastore.connect_to_signal('Deleted', _datastore_deleted_cb)

    return _datastore
_datastore = _get_datastore()

class ActivityLauncher:
    def __init__(self):
        self.status_icon = Gtk.StatusIcon()
        self.status_icon.connect("activate", self.click_event)
        self.status_icon.connect("popup-menu", self.click_event)
        self.randomize_icon()

    def randomize_icon(self):
        randiconfile = "Favicon_" + str(randint(1,12)).zfill(2) + ".png"
        self.status_icon.set_from_file(os.path.join("icons/", randiconfile))

    def make_submenu(self, bundle):
        submenu = Gtk.Menu()

        newitem = MenuItem(icon_name='activity-start')
        newitem.set_label("Start new")
        newitem.connect("activate", self.launch, bundle)
        submenu.append(newitem)

        results, n = _datastore.find(
                            {'limit':10, 
                             'activity':bundle.get_bundle_id()},
                            ['uid', 'title', 'mime_type'])

        if n>0:
            separator = Gtk.SeparatorMenuItem()
            submenu.append(separator)

        for i in results:
            title = ''.join([chr(byte) for byte in i['title']])
            uid = i['uid']

            item = MenuItem(file_name=bundle.get_icon(),
                            xo_color=xocolor.XoColor())
            item.set_label(title)
            item.connect("activate", self.launch_with_uid, bundle, uid)
            submenu.append(item)

        if n>0:
            separator = Gtk.SeparatorMenuItem()
            submenu.append(separator)

        view_source = MenuItem(icon_name='view-source')
        view_source.set_label("View Source")
        view_source.connect("activate", self.view_source, bundle)
        submenu.append(view_source)

        return submenu

    def refresh_activity_list(self):
        self.menu = Gtk.Menu()

        def process_dir(activity_path):
            for dir_name in sorted(os.listdir(activity_path)):
                bundles_installed = []
                if dir_name.endswith('.activity'):
                    bundle_dir = os.path.join(activity_path, dir_name)
                    bundle = ActivityBundle(bundle_dir)
                    bundles_installed.append(bundle)

                    item = MenuItem(file_name=bundle.get_icon(),
                                    xo_color=xocolor.XoColor())
                    item.set_label(bundle.get_name())
                    item.set_reserve_indicator(True)
                    item.set_submenu(self.make_submenu(bundle))
                    self.menu.append(item)

        process_dir('/usr/share/sugar/activities/')
        process_dir(activities_path) # ~/Activities

        separator = Gtk.SeparatorMenuItem()
        self.menu.append(separator)

        about = MenuItem()
        about.set_label("About")
        about.connect("activate", self.show_about_dialog)
        self.menu.append(about)

        quit = MenuItem()
        quit.set_label("Quit")
        quit.connect("activate", Gtk.main_quit)
        self.menu.append(quit)

        self.menu.show_all()

    def handle_menu(self, widget):
        widget.get_submenu().popdown()
        return True

    def click_event(self, *data):
        time = Gtk.get_current_event_time()
        self.refresh_activity_list()
        self.menu.popup(None, None, None, self.status_icon, 0, time)

    def launch(self, widget, bundle):
        os.chdir (bundle.get_path())
        import subprocess
        subprocess.Popen(bundle.get_command(), shell=True)

    def launch_with_uid(self, widget, bundle, uid):
        os.chdir (bundle.get_path())
        import subprocess
        subprocess.Popen(bundle.get_command()+' -o '+uid, shell=True)

    def view_source(self, widget, bundle):
        os.chdir (bundle.get_path())
        import subprocess
        subprocess.Popen("xdg-open "+bundle.get_path(), shell=True)

    def show_about_dialog(self, widget):
        about_dialog = Gtk.AboutDialog()

        about_dialog.set_destroy_with_parent(True)
        about_dialog.set_name("sugar-launcher-applet")
        about_dialog.set_version("0.1")
        about_dialog.set_authors(["Sebastian Silva"])

        about_dialog.run()
        about_dialog.destroy()

if __name__=='__main__':
    app = ActivityLauncher()
    Gtk.main()
