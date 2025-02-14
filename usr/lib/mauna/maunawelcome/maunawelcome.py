#!/usr/bin/python3
import gettext
import locale
import os
import platform
import subprocess

import apt
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

NORUN_FLAG = os.path.expanduser("~/.mauna/maunawelcome/norun.flag")

# i18n
gettext.install("maunawelcome", "/usr/share/mauna/locale")
from locale import gettext as _

locale.bindtextdomain("maunawelcome", "/usr/share/mauna/locale")
locale.textdomain("maunawelcome")

LAYOUT_STYLE_LEGACY, LAYOUT_STYLE_NEW = range(2)

class SidebarRow(Gtk.ListBoxRow):

    def __init__(self, page_widget, page_name, icon_name):
        Gtk.ListBoxRow.__init__(self)
        self.page_widget = page_widget
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.set_border_width(6)
        image = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
        box.pack_start(image, False, False, 0)
        label = Gtk.Label()
        label.set_text(page_name)
        box.pack_start(label, False, False, 0)
        self.add(box)


class MaunaWelcome():

    def __init__(self):
        builder = Gtk.Builder()
        builder.set_translation_domain("maunawelcome")
        builder.add_from_file('/usr/share/mauna/maunawelcome/maunawelcome.ui')

        window = builder.get_object("main_window")
        window.set_icon_name("maunawelcome")
        window.set_position(Gtk.WindowPosition.CENTER)
        window.connect("destroy", Gtk.main_quit)

        with open("/etc/mauna/info") as f:
            config = dict([line.strip().split("=") for line in f])
        codename = config['CODENAME'].capitalize()
        edition = config['EDITION'].replace('"', '')
        release = config['RELEASE']
        desktop = config['DESKTOP']
#        release_notes = config['RELEASE_NOTES_URL']
#        new_features = config['NEW_FEATURES_URL']
        architecture = "64-bit"
        if platform.machine() != "x86_64":
            architecture = "32-bit"

        # distro-specific
        dist_name = "Mauna Linux"
        if os.path.exists("/usr/share/doc/debian-system-adjustments/copyright"):
            dist_name = "Mauna"

        # Setup the labels in the Mint badge
        builder.get_object("label_version").set_text("%s %s" % (dist_name, release))
        builder.get_object("label_edition").set_text("%s %s" % (edition, architecture))

        # Setup the main stack
        self.stack = Gtk.Stack()
        builder.get_object("center_box").pack_start(self.stack, True, True, 0)
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(150)

        # Action buttons
        builder.get_object("button_forums").connect("clicked", self.visit, "https://forum.maunalinux.top")
        builder.get_object("button_contribute").connect("clicked", self.visit, "https://maunalinux.top/donate")
        builder.get_object("button_update").connect("clicked", self.launch, "mauna-update")
        builder.get_object("button_software").connect("clicked", self.launch, "maunainstall")
        builder.get_object("button_timeshift").connect("clicked", self.pkexec, "timeshift-gtk")
        builder.get_object("button_gufw").connect("clicked", self.launch, "gufw")
        builder.get_object("go_button").connect("clicked", self.go)

        # Settings button depends on DE
        if os.getenv("XDG_CURRENT_DESKTOP") in ["Cinnamon", "X-Cinnamon"]:
            builder.get_object("button_settings").connect("clicked", self.launch, "cinnamon-settings")
        elif os.getenv("XDG_CURRENT_DESKTOP") == "MATE":
            builder.get_object("button_settings").connect("clicked", self.launch, "mate-control-center")
        elif os.getenv("XDG_CURRENT_DESKTOP") == "XFCE":
            builder.get_object("button_settings").connect("clicked", self.launch, "xfce4-settings-manager")
        elif os.getenv("XDG_CURRENT_DESKTOP") == "BUDGIE":
            builder.get_object("button_settings").connect("clicked", self.launch, "gnome-control-center")
        elif os.getenv("XDG_CURRENT_DESKTOP") == "GNOME":
            builder.get_object("button_settings").connect("clicked", self.launch, "gnome-control-center")
        elif os.getenv("XDG_CURRENT_DESKTOP") == "KDE":
            builder.get_object("button_settings").connect("clicked", self.launch, "systemsettings")
        else:
            # Hide settings
            builder.get_object("box_first_steps").remove(builder.get_object("box_colors"))
            builder.get_object("box_first_steps").remove(builder.get_object("box_settings"))

        # Construct the stack switcher
        self.list_box = builder.get_object("list_navigation")

        page = builder.get_object("page_home")
        self.stack.add_named(page, "page_home")
        self.list_box.add(SidebarRow(page, _("Welcome"), "go-home-symbolic"))
        self.stack.set_visible_child(page)

        page = builder.get_object("page_first_steps")
        self.stack.add_named(page, "page_first_steps")
        self.first_steps_row = SidebarRow(page, _("First Steps"), "dialog-information-symbolic")
        self.list_box.add(self.first_steps_row)

        page = builder.get_object("page_help")
        self.stack.add_named(page, "page_help")
        self.list_box.add(SidebarRow(page, _("Help"), "help-browser-symbolic"))

        page = builder.get_object("page_contribute")
        self.stack.add_named(page, "page_contribute")
        self.list_box.add(SidebarRow(page, _("Contribute"), "starred-symbolic"))

        self.list_box.connect("row-activated", self.sidebar_row_selected_cb)

        # Construct the bottom toolbar
        box = builder.get_object("toolbar_bottom")
        checkbox = Gtk.CheckButton()
        checkbox.set_label(_("Show this dialog at startup"))
        if not os.path.exists(NORUN_FLAG):
            checkbox.set_active(True)
        checkbox.connect("toggled", self.on_button_toggled)
        box.pack_end(checkbox)

        window.set_default_size(800, 500)
        window.show_all()

    def go(self, button):
        self.list_box.select_row(self.first_steps_row)
        self.stack.set_visible_child_name("page_first_steps")

    def sidebar_row_selected_cb(self, list_box, row):
        self.stack.set_visible_child(row.page_widget)

    def on_button_toggled(self, button):
        if button.get_active():
            if os.path.exists(NORUN_FLAG):
                os.system("rm -rf %s" % NORUN_FLAG)
        else:
            os.system("mkdir -p ~/.mauna/maunawelcome")
            os.system("touch %s" % NORUN_FLAG)

    def visit(self, button, url):
        subprocess.Popen(["xdg-open", url])

    def launch(self, button, command):
        subprocess.Popen([command])

    def pkexec(self, button, command):
        subprocess.Popen(["pkexec", command])

if __name__ == "__main__":
    MaunaWelcome()
    Gtk.main()
