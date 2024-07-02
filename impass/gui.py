from __future__ import annotations

import os
import gi  # type: ignore

from typing import Any, Optional, Dict, Callable

from .db import pwgen, DEFAULT_NEW_PASSWORD_OCTETS, Database

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore # noqa: E402
from gi.repository import GObject  # noqa: E402
from gi.repository import Gdk  # noqa: E402
from gi.repository import Gio  # noqa: E402


############################################################

class Gui:
    """Impass GTK-based query UI."""

    def __init__(self, db: Database, query: Optional[str] = None) -> None:
        """
        +--------------------- warning --------------------+
        |                    notification                  |
        +--------------------------------------------------+
        |                    description                   |
        +----------------- simplebox ----------------------+
        | [_simplectxentry____] <simplebtn> <simplemenubtn>|
        +------------------- ctxbox -----------------------+
        |          | +----- ctxbox2 -----------------------+
        | ctxlabel | | [_ctxentry________________________] |
        |          | +---------------- --------------------+ (ctxwarninglabel shows when
        |          | | ctxwarninglabel                     |  ctxentry matches existing
        |          | +-------------------------------------+  entry (createbtn is also
        +------------------- passbox ----------------------+  disabled in this case))
        |           +------ passbox2 --------+             |
        | passlabel | [_passentry__________] | <createbtn> | createbtn saves, emits, and
        |           | passdescription        |             | closes
        +-----------+------------------------+-------------+
        """
        self.db = db
        self.query = query
        self.selected: Optional[Dict[str, str]] = None
        self.window: Gtk.Window
        self.entry: Gtk.Entry
        self.label: Gtk.Label
        self.app: Gtk.Application
        if query is not None:
            query = query.strip()

        if query:
            # If we have an intial query, directly do a search without
            # initializing any Gtk objects.  This will initialize the
            # database and potentially return entries.
            r = self.db.search(query)
            # If only a single entry is found, _search() will set the
            # result and attempt to close any X objects (of which
            # there are none).  Since we don't need to initialize any
            # GUI, return the initialization immediately.
            # See .returnValue().
            if len(r) == 1:
                self.selected = r[list(r.keys())[0]]
                return

        self.app = Gtk.Application(application_id='net.cmrg.impass')
        self.app.connect('activate', self.on_activate)

    def on_activate(self, app: Gtk.Application) -> None:
        self.window = Gtk.ApplicationWindow(application=app)
        self.window.set_title('🔒impass')

        self.frame = Gtk.Box(name="frame",
                             orientation=Gtk.Orientation.VERTICAL)
        self.window.set_child(self.frame)

        self.css = Gtk.CssProvider()
        self.css.load_from_string('''
        label.warning {
          color: red;
        }
        label.info {
          font-style: italic;
        }
        popover.nondefaultaction contents {
          border-top-left-radius: 0px;
          border-top-right-radius: 0px;
        }
        popover.completion contents {
          border-radius: 0px;
          padding: 1px;
        }
        popover.completion contents button {
          padding: 0px;
          min-height: 1em;
          min-width: 20em;
          border-radius: 0px;
        }
        popover.completion contents button:focus {
          background: @theme_selected_bg_color;
          color: @selected_fg_color;
        }
        ''')

        self.warning = Gtk.Box(name="warning",
                               orientation=Gtk.Orientation.VERTICAL,
                               visible=False)
        self.frame.append(self.warning)
        self.notification = Gtk.Label(name="notification",
                                      css_classes=["warning"],
                                      label='⚠ could not validate signature on db file!')
        self.warning.append(self.notification)
        self.warning.append(Gtk.Separator())


        self.description = Gtk.Label(name="description",
                                     label="Global state of impass gui")
        self.frame.append(self.description)
        self.simplebox = Gtk.Box(name="simplebox")
        self.frame.append(self.simplebox)
        self.entry = Gtk.Entry(name="simplectxentry",
                               hexpand=True,
                               width_chars=50,
                               placeholder_text="Enter context…")
        self.simplebox.append(self.entry)
        self.simplebtn = Gtk.Button(name="simplebtn",
                                    label="Emit")
        self.simplebox.append(self.simplebtn)
        self.simplemenubtn = Gtk.MenuButton(name="simplemenubtn")
        self.simplebox.append(self.simplemenubtn)
        
        self.ctxbox = Gtk.Box(name="ctxbox",
                              visible=False)
        self.frame.append(self.ctxbox)
        self.ctxlabel = Gtk.Label(name="ctxlabel",
                                  label="Context:")
        self.ctxbox.append(self.ctxlabel)
        self.ctxbox2 = Gtk.Box(name="ctxbox2",
                               orientation=Gtk.Orientation.VERTICAL)
        self.ctxbox.append(self.ctxbox2)
        self.ctxentry = Gtk.Entry(name="ctxentry",
                                  hexpand=True,
                                  placeholder_text="Enter context…")
        self.ctxbox2.append(self.ctxentry)
        self.ctxwarninglabel = Gtk.Label(name="ctxwarninglabel",
                                         visible=False,
                                         css_classes=['warning'],
                                         label="⚠ This context already exists!")
        self.ctxbox2.append(self.ctxwarninglabel)

        self.passbox = Gtk.Box(name="passbox",
                               visible=False)
        self.frame.append(self.passbox)
        self.passlabel = Gtk.Label(name="passlabel",
                                   label="Password:")
        self.passbox.append(self.passlabel)
        self.passbox2 = Gtk.Box(name="passbox2",
                                orientation=Gtk.Orientation.VERTICAL)
        self.passbox.append(self.passbox2)
        self.passentry = Gtk.Entry(name="passentry",
                                   hexpand=True,
                                   visibility=False,
                                   primary_icon_name="view-refresh",
                                   secondary_icon_name="edit-find",
                                   primary_icon_tooltip_text="generate a new password",
                                   secondary_icon_tooltip_text="show_password",
                                   placeholder_text="You must enter a password",
                                   input_purpose=Gtk.InputPurpose.PASSWORD)
        self.passbox2.append(self.passentry)
        self.passdescription = Gtk.Label(name="passdescription",
                                         css_classes=['info'],
                                         label="%d characters, %d lowercase, etc…")
        self.passbox2.append(self.passdescription)
        self.createbtn = Gtk.Button(name="createbtn",
                                    label="Create and emit",
                                    receives_default=True)
        self.passbox.append(self.createbtn)

        self.completion = Gtk.Popover(name="completion",
                                      position=Gtk.PositionType.BOTTOM,
                                      halign=Gtk.Align.START,
                                      has_arrow=False,
                                      css_classes=['completion','background'],
                                      autohide=False)
        self.completionbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.completion.set_child(self.completionbox)
        self.simplebox.append(self.completion)

        delaction = Gio.SimpleAction.new("delete", None)
        delaction.connect("activate", self.deleteclicked)
        self.window.add_action(delaction)
        emitmenu = Gio.Menu()
        emitmenu.insert(0, 'Delete', 'win.delete')
        self.emitmenu = Gtk.PopoverMenu(name="emitmenu",
                                        menu_model=emitmenu,
                                        has_arrow=False,
                                        halign=Gtk.Align.END,
                                        css_classes=["nondefaultaction", "background"],
                                        position=Gtk.PositionType.BOTTOM)

        createmenu = Gio.Menu()
        customaction = Gio.SimpleAction.new("createcustom", None)
        customaction.connect("activate", self.customclicked)
        self.window.add_action(customaction)
        createmenu.insert(0, 'Create custom…', 'win.createcustom')
        self.createmenu = Gtk.PopoverMenu(name="createmenu",
                                          menu_model=createmenu,
                                          has_arrow=False,
                                          halign=Gtk.Align.END,
                                          css_classes=["nondefaultaction", "background"],
                                          position=Gtk.PositionType.BOTTOM)
        
        self.warning.set_visible(not self.db.sigvalid)

        refreshpassaction = Gio.SimpleAction.new("refreshpass", None)
        refreshpassaction.connect("activate", self.refreshpass)
        self.window.add_action(refreshpassaction)
        showpassaction = Gio.SimpleAction.new("showpass", None)
        showpassaction.connect("activate", self.showhidepass)
        self.window.add_action(showpassaction)

        self.passmenu = Gio.Menu()
        self.passmenu.insert(0, 'Generate a new password', 'win.refreshpass')
        self.passmenu.insert(1, 'Show password', 'win.showpass')
        self.passentry.set_extra_menu(self.passmenu)

        self.eck = Gtk.EventControllerKey()
        self.eck.connect('key-pressed', self.keypress)
        self.window.add_controller(self.eck)
        Gtk.StyleContext().add_provider_for_display(self.window.get_display(), self.css,
                                                    Gtk.STYLE_PROVIDER_PRIORITY_USER)

        self.window.connect("destroy", self.destroy)
        self.entry.connect("activate", self.simpleclicked)
        self.entry.connect("changed", self.update_simple_context_entry)
        # FIXME: add alternate context menu items
        #self.entry.connect("populate-popup", self.simple_ctx_popup)
        self.simplebtn.connect("clicked", self.simpleclicked)
        self.ctxentry.connect("changed", self.update_ctxentry)
        self.ctxentry.connect("activate", self.customcreateclicked)
        self.passentry.connect("changed", self.update_passentry)
        self.passentry.connect("activate", self.customcreateclicked)
        self.passentry.connect("icon-press", self.passentry_icon_clicked)
        self.createbtn.connect("clicked", self.customcreateclicked)

        if self.query:
            self.entry.set_text(self.query)
        self.set_state("Enter context for desired password:")
        self.update_simple_context_entry(None)
        self.window.present()

    def set_state(self, state: str) -> None:
        self.description.set_label(state)

    def update_simple_context_entry(self, widget: Optional[Gtk.Widget]) -> None:
        sctx = self.entry.get_text().strip()
        max_matches = 40
        matches = []
        
        if sctx is not None and sctx != '':
            matches = sorted(filter(lambda x: sctx.lower() in x.lower(), self.db))[:max_matches]
        if len(matches) == 0:
            self.completion.set_visible(False)
        else:
            m:Optional[Gtk.Widget] = self.completionbox.get_first_child()
            while m is not None:
                self.completionbox.remove(m)
                m = self.completionbox.get_first_child()
            for m in matches:
                b = Gtk.Button(label=m,
                               halign=Gtk.Align.START)
                b.get_first_child().set_halign(Gtk.Align.START)
                self.completionbox.append(b)
                b.connect("clicked", lambda x: self.entry.set_text(x.get_label()))
            self.completion.set_visible(True)

        if sctx in self.db:
            self.simplebtn.set_label("Emit")
            self.simplemenubtn.set_popover(self.emitmenu)
        elif sctx is None or sctx == "":
            self.simplebtn.set_label("Create…")
            self.simplemenubtn.set_popover(None)
        else:
            self.simplebtn.set_label("Create")
            self.simplemenubtn.set_popover(self.createmenu)


    def add_to_menu(
        self,
        menu: Gtk.Widget,
        name: str,
        onclicked: Callable[[Gui], None],
        position: int,
    ) -> None:
        x = Gtk.MenuItem(label=name)
        x.connect("activate", onclicked)
        x.show()
        menu.insert(x, position)

    def simple_ctx_popup(
        self, entry: Gtk.Widget, widget: Gtk.Widget, data: Optional[Any] = None
    ) -> None:
        sctx = self.entry.get_text().strip()
        if sctx in self.db:
            self.add_to_menu(
                widget, "Emit password for '" + sctx + "'", self.simpleclicked, 0
            )
            self.add_to_menu(
                widget, "Delete password for '" + sctx + "'", self.deleteclicked, 1
            )
            pos = 2
        elif sctx is None or sctx == "":
            self.add_to_menu(widget, "Create custom password…", self.customclicked, 0)
            pos = 1
        else:
            self.add_to_menu(
                widget, "Create and emit password for '" + sctx + "'", self.create, 0
            )
            self.add_to_menu(
                widget,
                "Create custom password for '" + sctx + "'…",
                self.customclicked,
                1,
            )
            pos = 2
        sep = Gtk.SeparatorMenuItem()
        sep.show()
        widget.insert(sep, pos)

    def simpleclicked(self, widget: Gtk.Widget) -> None:
        sctx = self.entry.get_text().strip()
        if sctx in self.db:
            self.selected = self.db[sctx]
            if self.selected is None:
                self.label.set_text(
                    "weird -- no context found even though there should be one"
                )
            else:
                self.window.close()
        elif sctx is None or sctx == "":
            self.customclicked(None)
        else:
            self.create(None)

    def keypress(self, keycontroller: Gtk.EventControllerKey, key: int, code: int, mods: Gdk.ModifierType) -> None:
        if key == Gdk.KEY_Escape:
            if self.completion.get_visible():
                self.completion.set_visible(False)
            else:
                self.app.quit()

    def create(self, widget: Gtk.Widget, data: Optional[Any] = None) -> None:
        sctx = self.entry.get_text().strip()
        self.selected = self.db.add(sctx)
        self.db.save()
        self.window.close()

    def deleteclicked(self, action: Gio.Action, param: GLib.Variant) -> None:
        sctx = self.entry.get_text().strip()
        confirmation = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            message_type=Gtk.MessageType.QUESTION,
            text="Are you sure you want to delete the password for '" + sctx + "'?",
        )
        def delok(_: Optional[Gtk.Widget]) -> None:
            self.db.remove(sctx)
            self.db.save()
            confirmation.close()
            self.window.close()

        ok = confirmation.get_widget_for_response(Gtk.ResponseType.OK)
        ok.connect('clicked', delok)
        cancel = confirmation.get_widget_for_response(Gtk.ResponseType.CANCEL)
        cancel.connect('clicked', lambda x: confirmation.close())
        confirmation.present()

    def customclicked(self, action: Gio.Action, param: GLib.Variant) -> None:
        if self.ctxentry is None or self.entry is None:
            raise Exception("Gui is not initialized")
        self.simplebox.set_visible(False)
        self.ctxbox.set_visible(True)
        self.passbox.set_visible(True)
        self.ctxentry.set_text(self.entry.get_text())
        selection = self.entry.get_selection_bounds()
        if selection:
            self.ctxentry.select_region(selection[0], selection[1])
        else:
            self.ctxentry.set_position(self.entry.get_position())
        self.ctxentry.grab_focus_without_selecting()
        self.set_state("Create new password (with custom settings):")
        self.refreshpass()
        self.update_ctxentry()

    def update_ctxentry(
        self, widget: Optional[Gtk.Widget] = None, data: Optional[Any] = None
    ) -> None:
        sctx = self.ctxentry.get_text().strip()
        if sctx in self.db:
            self.ctxwarninglabel.set_visible(True)
            self.ctxwarninglabel.set_text("The context '%s' already exists!" % (sctx))
            self.createbtn.set_sensitive(False)
        elif sctx is None or sctx == "":
            self.ctxwarninglabel.set_visible(False)
            self.createbtn.set_sensitive(False)
        else:
            self.ctxwarninglabel.set_visible(False)
            self.createbtn.set_sensitive(self.passentry.get_text() != "")

    def update_passentry(
        self, widget: Optional[Gtk.Widget] = None, data: Optional[Any] = None
    ) -> None:
        newpass = self.passentry.get_text()
        sctx = self.ctxentry.get_text().strip()
        ln = len(newpass)
        # FIXME: should check (and warn) for non-ascii characters
        lcount = len("".join(filter(lambda x: x.islower(), newpass)))
        ucount = len("".join(filter(lambda x: x.isupper(), newpass)))
        ncount = len("".join(filter(lambda x: x.isnumeric(), newpass)))
        ocount = ln - (lcount + ucount + ncount)
        desc = "%d characters (%d lowercase, %d uppercase, %d number, %d other)" % (
            ln,
            lcount,
            ucount,
            ncount,
            ocount,
        )
        self.createbtn.set_sensitive(
            newpass != "" and sctx != "" and sctx not in self.db
        )
        self.passdescription.set_text(desc)

    def passentry_icon_clicked(
        self,
        widget: Gtk.Widget,
        pos: Gtk.EntryIconPosition,
        data: Optional[Any] = None,
    ) -> None:
        if pos == Gtk.EntryIconPosition.PRIMARY:
            self.refreshpass()
        elif pos == Gtk.EntryIconPosition.SECONDARY:
            self.showhidepass()

    def showhidepass(self,
                     action: Optional[Gio.Action] = None,
                     param: Optional[GLib.Variant] = None) -> None:
        newvis = not self.passentry.get_visibility()
        self.passentry.set_visibility(newvis)
        label = "Hide password" if newvis else "Show password"
        self.passentry.set_icon_tooltip_text(Gtk.EntryIconPosition.SECONDARY, label)
        self.passmenu.remove(1)
        self.passmenu.insert(1, label, 'win.showpass')

    def refreshpass(self, action: Optional[Gio.Action] = None, param: Optional[GLib.Variant] = None) -> None:
        pwsize = os.environ.get("IMPASS_PASSWORD", DEFAULT_NEW_PASSWORD_OCTETS)
        try:
            pwsize = int(pwsize)
        except ValueError:
            pwsize = DEFAULT_NEW_PASSWORD_OCTETS
        newpw = pwgen(pwsize)
        self.passentry.set_text(newpw)
        # FIXME: should refocus self.passentry?

    def customcreateclicked(
        self, widget: Optional[Gtk.Widget] = None, event: Optional[Gdk.Event] = None
    ) -> None:
        newctx = self.ctxentry.get_text().strip()
        newpass = self.passentry.get_text()
        if newpass == "" or newctx == "" or newctx in self.db:
            # this button is not supposed to work under these conditions
            return
        self.selected = self.db.add(newctx, password=newpass)
        self.db.save()
        self.window.close()

    def destroy(self, widget: Gtk.Widget, data: Optional[Any] = None) -> None:
        self.window.close()

    def return_value(self) -> Optional[Dict[str, str]]:
        if self.selected is None:
            self.app.run()
        return self.selected
