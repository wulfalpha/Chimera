#!/usr/bin/env python3
import logging
import subprocess as process

import gi

gi.require_version("Gtk", "3.0")
import threading
from gi.repository import GLib, Gtk

LABEL_CHECK_FOR_UPDATES = "Check for updates"
LABEL_INSTALL_UPDATES = "Install Updates"
LABEL_QUIT = "Quit"
TITLE_CHIMERA_UPDATE = "Chimera Update"
TITLE_CHIMERA_UPDATE_ERROR = "Chimera Update Error"
UPDATE_READY = "Updates: Ready..."
UPDATE_CHECKING = "Updates: Checking..."
ERROR_UNABLE_TO_CHECK = "Unable to check for updates"
ERROR_UNABLE_TO_PARSE = "Unable to parse update count"
ERROR_FAILED_TO_RUN_COMMAND = "Failed to run command: {cmd}"


class ChimeraWindow(Gtk.Window):
    """Create the GTK window"""

    def __init__(self, package_manager):
        super().__init__(title="Chimera Updater (GTK)")
        self.set_border_width(10)
        self.set_default_size(640, 200)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(True)
        self.package_manager = package_manager
        frame1 = Gtk.Frame(label="Chimera Update")
        grid1 = Gtk.Grid(row_spacing=10, column_spacing=10, column_homogeneous=True)
        self.label1 = Gtk.Label(label="Updates: Ready...")
        self.label1.set_hexpand(True)

        self.spinner = Gtk.Spinner()
        self.spinner.set_hexpand(True)
        self.spinner.set_vexpand(True)

        button_updates = self.__create_button(
            LABEL_CHECK_FOR_UPDATES, "Checker", self.on_button_updates_clicked, True
        )
        self.button_upgrade = self.__create_button(
            LABEL_INSTALL_UPDATES, "Installer", self.on_button_upgrade_clicked, False
        )
        button_q = self.__create_button(LABEL_QUIT, "Quit", Gtk.main_quit, True)

        grid1.attach(self.label1, 0, 2, 3, 2)
        grid1.attach(self.spinner, 0, 4, 3, 2)
        grid1.attach(button_updates, 0, 8, 1, 1)
        grid1.attach(self.button_upgrade, 1, 8, 1, 1)
        grid1.attach(button_q, 2, 8, 1, 1)
        frame1.add(grid1)
        self.add(frame1)  # don't forget to add the frame to the window

    def __create_button(self, label, tooltip_text, event_handler, is_sensitive):
        button = Gtk.Button(label=label)
        button.set_hexpand(True)
        button.set_sensitive(is_sensitive)
        button.set_tooltip_text(tooltip_text)
        button.connect("clicked", event_handler)
        return button

    def update_results(self, updates):
        """Display results of update procedure."""
        if updates == 0:
            update_msg = "Your system is up-to-date."
            self.send_notification(
                "Chimera Update", "Your system is up-to-date.", False
            )
        elif updates == 1:
            update_msg = "There is one update available."
            self.send_notification(
                "Chimera Update", "There is one update available.", False
            )
        else:
            update_msg = f"There are {updates} updates available."
            self.send_notification(
                "Chimera Update", f"There are {updates} updates available.", False
            )
        self.label1.set_text(f"Updates: {update_msg}")
        self.button_upgrade.set_sensitive(updates > 0)
        self.spinner.stop()

    def set_update_label(self, msg):
        """Actual display for number of updates"""
        self.label1.set_text(f"Updates: {msg}")

    def on_button_updates_clicked(self, widget):
        """Button to start the update procedure."""
        GLib.idle_add(self.spinner.start)
        GLib.idle_add(self.label1.set_text, "Updates: Checking...")
        threading.Thread(target=self.run_update_check).start()

    def run_update_check(self):
        """Actually check for updates and account for error process."""
        print(self.package_manager.check_updates())
        update_process = self.package_manager.check_updates()
        if update_process.returncode != 0:
            GLib.idle_add(self.show_error, "Unable to check for updates")
            return

        updates = update_process.stdout.strip()
        try:
            updates = int(updates)
        except ValueError:
            GLib.idle_add(self.show_error, "Unable to parse update count")
        return
        GLib.idle_add(self.update_results, updates)

    def show_error(self, message):
        self.label1.set_text(f"Error: {message}")
        self.send_notification(TITLE_CHIMERA_UPDATE_ERROR, message, True)
        self.spinner.stop()

    def on_button_upgrade_clicked(self, widget):
        GLib.idle_add(self.spinner.start)
        GLib.idle_add(self.label1.set_text, UPDATE_CHECKING)
        threading.Thread(target=self.run_upgrade).start()

    def run_upgrade(self):
        """Do the upgrade."""
        upgrade_process = self.package_manager.upgrade()
        if upgrade_process.returncode != 0:
            GLib.idle_add(self.show_error, "Unable to perform upgrade")
            return
        GLib.idle_add(self.update_after_upgrade)

    def update_after_upgrade(self):
        """Reset label after update."""
        self.label1.set_text("Updates: Update Complete!")
        self.send_notification(
            "Chimera Update", "Update complete! Your system is up-to-date.", False
        )
        self.spinner.stop()

    def send_notification(self, title, message, urgent):
        try:
            if urgent:
                process.run(["notify-send", title, message, "-u", "critical"])
            else:
                process.run(["notify-send", title, message])
        except Exception as e:
            logging.error(str(e))
            raise Exception(f"Failed to run command: {cmd}")


def run_command(cmd):
    try:
        result = process.run(cmd, shell=True, capture_output=True, text=True)
        print(result)
        if result.stderr:
            logging.error(f"Command error output: {result.stderr}")
    except process.CalledProcessError as cpe:
        logging.error(f"Command failed with exit code {cpe.returncode}")
        logging.error(str(cpe))
        raise Exception(ERROR_FAILED_TO_RUN_COMMAND.format(cmd=cmd)) from cpe


class PackageManager:
    """Package manager class"""

    def __init__(self):
        self.check_updates_cmd = ""
        self.count_updates_cmd = ""
        self.upgrade_cmd = ""

    def check_updates(self):
        """how the package manager checks for updates"""
        return run_command(self.check_updates_cmd)

    def count_updates(self):
        """Return number of update process."""
        return run_command(self.count_updates_cmd)

    def upgrade(self):
        """Upgrade packages"""
        return run_command(self.upgrade_cmd)


class AptManager(PackageManager):
    """Provide support for Debian distros"""

    def __init__(self):
        super().__init__()
        self.check_updates_cmd = "apt-get -q update"
        self.count_updates_cmd = "apt-get -q -y --ignore-hold --allow-change-held-packages \
                                  --allow-unauthenticated -s dist-upgrade | grep ^Inst | wc -l"
        self.upgrade_cmd = "apt upgrade -y"


class NalaManager(AptManager):
    """Add nala support"""

    def __init__(self):
        super().__init__()
        self.upgrade_cmd = "nala upgrade -y"


class DnfManager(PackageManager):
    """Support for dnf package manager"""

    def __init__(self):
        super().__init__()
        self.count_updates_cmd = "dnf check-update | grep -v '^$' | wc -l"
        self.check_updates_cmd = "dnf check-update"
        self.upgrade_cmd = "dnf upgrade"


class PacmanManager(PackageManager):
    """Support for Pacman. Note aur helpers not included deliberately to avoid causing issue process."""

    def __init__(self):
        super().__init__()
        self.count_updates_cmd = "pacman -Qu | wc -l"
        self.check_updates_cmd = "pacman -Qu"
        self.upgrade_cmd = "pacman -Syu"


class DistroCheck:
    """Checks against a list of supported distributions,
    and provides a corresponding package manager iterable."""

    def __init__(self):
        self.distro_id = self.get_distro_id()
        self.package_managers = {
            "debian": [("nala", NalaManager), ("apt", AptManager)],
            "ubuntu": [("nala", NalaManager), ("apt", AptManager)],
            "fedora": [("dnf", DnfManager)],
            # 'centos': [('yum', YumManager)],
            "arch": [("pacman", PacmanManager)],
            "arcolinux": [("pacman", PacmanManager)],
        }

    def get_distro_id(self):
        """Pull distro id from OS-release"""
        filename = "/etc/os-release"
        logging.info(f"Reading distro ID from {filename}")
        try:
            with open(filename, "r") as f:
                lines = f.readlines()
            for line in lines:
                if line.startswith("ID="):
                    return line[3:].strip()
            raise Exception("Could not determine distro from /etc/os-release")
        except Exception as e:
            logging.error(f"Failed to read distro ID from {filename}. Error: {str(e)}")
            raise

    def get_package_manager_for_distro(self):
        """Select Package manager and account for error process.

        Returns:
            PackageManager subclass instance if a supported package
            manager is found for the current distribution.

        Raises:
            Exception: If no supported package manager is found.
        """
        options = self.package_managers.get(self.distro_id)
        if options is None:
            raise Exception(
                f"No supported package manager found for distro: {self.distro_id}"
            )
            # Iterate over the options and return the first available package manager
        for pkg_name, pkg_manager_class in options:
            if self.is_tool_available(pkg_name):
                return pkg_manager_class()
        raise Exception(
            f"No supported package manager available for distro: {self.distro_id}"
        )

    def is_tool_available(self, name):
        """Check for available package manager."""
        return (
            process.call(
                ["which", name], stdout=process.DEVNULL, stderr=process.DEVNULL
            )
            == 0
        )


class ErrorDialog(Gtk.Dialog):
    """Manage errors via dialogue box."""

    def __init__(self, parent, message):
        Gtk.Dialog.__init__(self, title="Error", transient_for=parent, flags=0)
        self.add_buttons(
            Gtk.STOCK_OK,
            Gtk.ResponseType.OK,
        )

        label = Gtk.Label(label=message)

        box = self.get_content_area()
        box.add(label)
        self.show_all()


try:
    distro_check = DistroCheck()
    package_manager = distro_check.get_package_manager_for_distro()
except Exception as e:
    error_dialog = ErrorDialog(None, str(e))
    response = error_dialog.run()

    if response == Gtk.ResponseType.OK:
        error_dialog.destroy()

    Gtk.main_quit()
else:
    win1 = ChimeraWindow(package_manager)
    win1.connect("destroy", Gtk.main_quit)
    win1.show_all()

Gtk.main()
