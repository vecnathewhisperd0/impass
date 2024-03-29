from __future__ import annotations

import os
import gi  # type: ignore

from typing import Any, Optional, Dict, Callable

from .db import pwgen, DEFAULT_NEW_PASSWORD_OCTETS, Database

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # type: ignore # noqa: E402
from gi.repository import GObject  # noqa: E402
from gi.repository import Gdk  # noqa: E402


############################################################


# Assumes that the func_data is set to the number of the text column in the
# model.
def _match_func(completion: Any, key: str, iter: int, column: str) -> bool:
    model = completion.get_model()
    text = model[iter][column]
    if text.lower().find(key.lower()) > -1:
        return True
    return False


_gui_layout = """<?xml version="1.0" encoding="UTF-8"?>
<!-- Generated with glade 3.20.0 -->
<interface>
  <requires lib="gtk+" version="3.20"/>
  <object class="GtkMenu" id="emitmenu">
    <property name="visible">True</property>
    <property name="can_focus">False</property>
    <property name="halign">end</property>
    <child>
      <object class="GtkImageMenuItem" id="deletemenuitem">
        <property name="label">gtk-delete</property>
        <property name="visible">True</property>
        <property name="can_focus">False</property>
        <property name="use_underline">True</property>
        <property name="use_stock">True</property>
      </object>
    </child>
  </object>
  <object class="GtkMenu" id="createmenu">
    <property name="visible">True</property>
    <property name="can_focus">False</property>
    <property name="halign">end</property>
    <child>
      <object class="GtkImageMenuItem" id="custommenuitem">
        <property name="label" translatable="yes">Create custom…</property>
        <property name="visible">True</property>
        <property name="can_focus">False</property>
        <property name="use_underline">True</property>
      </object>
    </child>
  </object>
  <object class="GtkWindow" id="impass-gui">
    <property name="can_focus">False</property>
    <property name="border_width">4</property>
    <property name="title" translatable="yes">impass</property>
    <property name="icon_name">dialog-password</property>
    <child>
      <object class="GtkBox">
        <property name="visible">True</property>
        <property name="can_focus">False</property>
        <property name="orientation">vertical</property>
        <child>
          <object class="GtkBox" id="warning">
            <property name="visible">False</property>
            <property name="can_focus">False</property>
            <property name="orientation">vertical</property>
            <child>
              <object class="GtkLabel" id="notification">
                <property name="visible">True</property>
                <property name="can_focus">False</property>
                <property name="label" translatable="yes"
>WARNING: could not validate signature on db file!</property>
                <attributes>
                  <attribute name="foreground" value="#cccc00000000"/>
                </attributes>
              </object>
              <packing>
                <property name="expand">False</property>
                <property name="fill">True</property>
                <property name="position">0</property>
              </packing>
            </child>
            <child>
              <object class="GtkSeparator">
                <property name="visible">True</property>
                <property name="can_focus">False</property>
              </object>
              <packing>
                <property name="expand">False</property>
                <property name="fill">True</property>
                <property name="position">1</property>
              </packing>
            </child>
          </object>
          <packing>
            <property name="expand">False</property>
            <property name="fill">True</property>
            <property name="position">0</property>
          </packing>
        </child>
        <child>
          <object class="GtkLabel" id="description">
            <property name="visible">True</property>
            <property name="can_focus">False</property>
            <property name="label">Global state of impass gui</property>
          </object>
          <packing>
            <property name="expand">True</property>
            <property name="fill">True</property>
            <property name="position">1</property>
          </packing>
        </child>
        <child>
          <object class="GtkBox" id="simplebox">
            <property name="visible">True</property>
            <property name="can_focus">False</property>
            <child>
              <object class="GtkEntry" id="simplectxentry">
                <property name="visible">True</property>
                <property name="can_focus">True</property>
                <property name="width_chars">50</property>
                <property name="placeholder_text" translatable="yes"
>Enter context…</property>
              </object>
              <packing>
                <property name="expand">True</property>
                <property name="fill">True</property>
                <property name="position">0</property>
              </packing>
            </child>
            <child>
              <object class="GtkButton" id="simplebtn">
                <property name="label" translatable="yes">Emit</property>
                <property name="visible">True</property>
                <property name="can_focus">True</property>
                <property name="receives_default">True</property>
              </object>
              <packing>
                <property name="expand">False</property>
                <property name="fill">True</property>
                <property name="position">1</property>
              </packing>
            </child>
            <child>
              <object class="GtkMenuButton" id="simplemenubtn">
                <property name="visible">True</property>
                <property name="can_focus">True</property>
                <property name="receives_default">True</property>
              </object>
              <packing>
                <property name="expand">False</property>
                <property name="fill">True</property>
                <property name="position">2</property>
              </packing>
            </child>
          </object>
          <packing>
            <property name="expand">False</property>
            <property name="fill">True</property>
            <property name="position">2</property>
          </packing>
        </child>
        <child>
          <object class="GtkBox" id="ctxbox">
            <property name="can_focus">False</property>
            <child>
              <object class="GtkLabel" id="ctxlabel">
                <property name="visible">True</property>
                <property name="can_focus">False</property>
                <property name="label" translatable="yes">Context:</property>
              </object>
              <packing>
                <property name="expand">False</property>
                <property name="fill">True</property>
                <property name="position">0</property>
              </packing>
            </child>
            <child>
              <object class="GtkBox" id="ctxbox2">
                <property name="visible">True</property>
                <property name="can_focus">False</property>
                <property name="orientation">vertical</property>
                <child>
                  <object class="GtkEntry" id="ctxentry">
                    <property name="visible">True</property>
                    <property name="can_focus">True</property>
                    <property name="placeholder_text"translatable="yes"
>Enter context…</property>
                  </object>
                  <packing>
                    <property name="expand">False</property>
                    <property name="fill">True</property>
                    <property name="position">0</property>
                  </packing>
                </child>
                <child>
                  <object class="GtkBox" id="ctxwarning">
                    <property name="visible">True</property>
                    <property name="can_focus">False</property>
                    <child>
                      <object class="GtkLabel" id="ctxwarninglabel">
                        <property name="visible">True</property>
                        <property name="can_focus">False</property>
                        <property name="label" translatable="yes"
>This context already exists!</property>
                        <attributes>
                          <attribute name="style" value="italic"/>
                          <attribute name="foreground" value="#cccc00000000"/>
                        </attributes>
                      </object>
                      <packing>
                        <property name="expand">True</property>
                        <property name="fill">True</property>
                        <property name="position">0</property>
                      </packing>
                    </child>
                  </object>
                  <packing>
                    <property name="expand">False</property>
                    <property name="fill">True</property>
                    <property name="position">1</property>
                  </packing>
                </child>
              </object>
              <packing>
                <property name="expand">True</property>
                <property name="fill">True</property>
                <property name="position">1</property>
              </packing>
            </child>
          </object>
          <packing>
            <property name="expand">False</property>
            <property name="fill">True</property>
            <property name="position">2</property>
          </packing>
        </child>
        <child>
          <object class="GtkBox" id="passbox">
            <property name="can_focus">False</property>
            <child>
              <object class="GtkLabel" id="passlabel">
                <property name="visible">True</property>
                <property name="can_focus">False</property>
                <property name="label" translatable="yes">Password:</property>
              </object>
              <packing>
                <property name="expand">False</property>
                <property name="fill">True</property>
                <property name="position">0</property>
              </packing>
            </child>
            <child>
              <object class="GtkBox" id="passbox2">
                <property name="visible">True</property>
                <property name="can_focus">False</property>
                <property name="orientation">vertical</property>
                <child>
                  <object class="GtkEntry" id="passentry">
                    <property name="visible">True</property>
                    <property name="visibility">False</property>
                    <property name="can_focus">True</property>
                    <property name="primary_icon_stock">gtk-refresh</property>
                    <property name="secondary_icon_stock">gtk-find</property>
                    <property name="primary_icon_tooltip_text" translatable="yes"
>generate a new password</property>
                    <property name="secondary_icon_tooltip_text" translatable="yes"
>show password</property>
                    <property name="placeholder_text" translatable="yes"
>You must enter a password!</property>
                    <property name="input_purpose">password</property>
                  </object>
                  <packing>
                    <property name="expand">False</property>
                    <property name="fill">True</property>
                    <property name="position">0</property>
                  </packing>
                </child>
                <child>
                  <object class="GtkLabel" id="passdescription">
                    <property name="visible">True</property>
                    <property name="can_focus">False</property>
                    <property name="label" translatable="yes"
>%d characters, %d lowercase, etc…</property>
                     <attributes>
                       <attribute name="style" value="italic"/>
                     </attributes>
                  </object>
                  <packing>
                    <property name="expand">False</property>
                    <property name="fill">True</property>
                    <property name="position">1</property>
                  </packing>
                </child>
              </object>
              <packing>
                <property name="expand">True</property>
                <property name="fill">True</property>
                <property name="position">1</property>
              </packing>
            </child>
            <child>
              <object class="GtkButton" id="createbtn">
                <property name="label" translatable="yes">Create and emit</property>
                <property name="visible">True</property>
                <property name="can_focus">True</property>
                <property name="receives_default">True</property>
              </object>
              <packing>
                <property name="expand">False</property>
                <property name="fill">True</property>
                <property name="position">2</property>
              </packing>
            </child>
          </object>
          <packing>
            <property name="expand">False</property>
            <property name="fill">True</property>
            <property name="position">3</property>
          </packing>
        </child>
      </object>
    </child>
  </object>
</interface>
"""


class Gui:
    """Impass X-based query UI."""

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
        |          | +----- ctxwarning --------------------+ (ctxwarning only shows when
        |          | | ctxwarninglabel                     |  ctxentry matches existing
        |          | +-------------------------------------+  entry (createbtn is also
        +------------------- passbox ----------------------+  disabled in this case))
        |           +------ passbox2 --------+             |
        | passlabel | [_passentry__________] | <createbtn> | createbtn saves, emits, and
        |           | passdescription        |             | closes
        +-----------+------------------------+-------------+
        """
        self.db = db
        self.query = None
        self.results = None
        self.selected: Optional[Dict[str, str]] = None
        self.window: Optional[Gtk.Widget] = None
        self.entry: Optional[Gtk.Widget] = None
        self.label: Optional[Gtk.Widget] = None
        if query is not None:
            query = query.strip()

        if query:
            # If we have an intial query, directly do a search without
            # initializing any X objects.  This will initialize the
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

        self.builder: Gtk.Builder = Gtk.Builder.new_from_string(
            _gui_layout, len(_gui_layout)
        )
        self.window = self.builder.get_object("impass-gui")
        self.entry = self.builder.get_object("simplectxentry")
        self.simplebtn = self.builder.get_object("simplebtn")
        self.simplemenubtn = self.builder.get_object("simplemenubtn")
        self.emitmenu = self.builder.get_object("emitmenu")
        self.createmenu = self.builder.get_object("createmenu")
        self.warning = self.builder.get_object("warning")
        self.ctxentry = self.builder.get_object("ctxentry")
        self.ctxwarning = self.builder.get_object("ctxwarning")
        self.ctxwarninglabel = self.builder.get_object("ctxwarninglabel")
        self.createbtn = self.builder.get_object("createbtn")
        self.passentry = self.builder.get_object("passentry")
        self.passdescription = self.builder.get_object("passdescription")

        self.simplebox = self.builder.get_object("simplebox")
        self.ctxbox = self.builder.get_object("ctxbox")
        self.passbox = self.builder.get_object("passbox")

        if self.db.sigvalid is False:
            self.warning.show()

        completion = Gtk.EntryCompletion()
        self.entry.set_completion(completion)
        liststore = Gtk.ListStore(GObject.TYPE_STRING)
        completion.set_model(liststore)
        completion.set_text_column(0)
        completion.set_match_func(_match_func, 0)  # 0 is column number
        context_len = 50
        for context in sorted(filter(lambda x: x == x.strip(), self.db), key=str.lower):
            if len(context) > context_len:
                context_len = len(context)
            liststore.append([context])
        self.window.connect("destroy", self.destroy)
        self.window.connect("key-press-event", self.keypress)
        self.entry.connect("activate", self.simpleclicked)
        self.entry.connect("changed", self.update_simple_context_entry)
        self.entry.connect("populate-popup", self.simple_ctx_popup)
        self.simplebtn.connect("clicked", self.simpleclicked)
        self.builder.get_object("deletemenuitem").connect(
            "activate", self.deleteclicked
        )
        self.builder.get_object("custommenuitem").connect(
            "activate", self.customclicked
        )
        self.ctxentry.connect("changed", self.update_ctxentry)
        self.ctxentry.connect("activate", self.customcreateclicked)
        self.passentry.connect("changed", self.update_passentry)
        self.passentry.connect("activate", self.customcreateclicked)
        self.passentry.connect("icon-press", self.passentry_icon_clicked)
        self.passentry.connect("populate-popup", self.passentry_popup)
        self.createbtn.connect("clicked", self.customcreateclicked)

        if query:
            self.entry.set_text(query)
        self.set_state("Enter context for desired password:")
        self.update_simple_context_entry(None)
        self.window.show()

    def set_state(self, state: str) -> None:
        self.builder.get_object("description").set_label(state)

    def update_simple_context_entry(self, widget: Optional[Gtk.Widget]) -> None:
        if self.entry is None:
            raise Exception("Gui is not initialized")
        sctx = self.entry.get_text().strip()

        if sctx in self.db:
            self.simplebtn.set_label("Emit")
            self.simplemenubtn.set_popup(self.emitmenu)
        elif sctx is None or sctx == "":
            self.simplebtn.set_label("Create…")
            self.simplemenubtn.set_popup(None)
        else:
            self.simplebtn.set_label("Create")
            self.simplemenubtn.set_popup(self.createmenu)

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
        if self.entry is None:
            raise Exception("Gui is not initialized")
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
        if self.entry is None:
            raise Exception("Gui is not initialized")
        sctx = self.entry.get_text().strip()
        if sctx in self.db:
            self.retrieve(None)
        elif sctx is None or sctx == "":
            self.customclicked(None)
        else:
            self.create(None)

    def keypress(self, widget: Gtk.Widget, event: Gdk.EventKey) -> None:
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()

    def retrieve(self, widget: Gtk.Widget, data: Optional[Any] = None) -> None:
        if self.entry is None or self.label is None:
            raise Exception("Gui is not initialized")
        sctx = self.entry.get_text().strip()
        if sctx in self.db:
            self.selected = self.db[sctx]
            if self.selected is None:
                self.label.set_text(
                    "weird -- no context found even though there should be one"
                )
            else:
                Gtk.main_quit()
        else:
            self.label.set_text("no match")

    def create(self, widget: Gtk.Widget, data: Optional[Any] = None) -> None:
        if self.entry is None:
            raise Exception("Gui is not initialized")
        sctx = self.entry.get_text().strip()
        self.selected = self.db.add(sctx)
        self.db.save()
        Gtk.main_quit()

    def deleteclicked(self, widget: Gtk.Widget) -> None:
        if self.entry is None:
            raise Exception("Gui is not initialized")
        sctx = self.entry.get_text().strip()
        confirmation = Gtk.MessageDialog(
            parent=self.window,
            modal=True,
            destroy_with_parent=True,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            message_type=Gtk.MessageType.QUESTION,
            text="Are you sure you want to delete the password for '" + sctx + "'?",
        )
        answer = confirmation.run()
        confirmation.destroy()
        if answer == Gtk.ResponseType.OK:
            self.selected = None
            self.db.remove(sctx)
            self.db.save()
            Gtk.main_quit()

    def customclicked(self, widget: Gtk.Widget) -> None:
        if self.ctxentry is None or self.entry is None:
            raise Exception("Gui is not initialized")
        self.simplebox.hide()
        self.ctxbox.show()
        self.passbox.show()
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
            self.ctxwarning.show()
            self.ctxwarninglabel.set_text("The context '%s' already exists!" % (sctx))
            self.createbtn.set_sensitive(False)
        elif sctx is None or sctx == "":
            self.ctxwarning.hide()
            self.createbtn.set_sensitive(False)
        else:
            self.ctxwarning.hide()
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
        event: Optional[Gdk.Event] = None,
        data: Optional[Any] = None,
    ) -> None:
        if pos == Gtk.EntryIconPosition.PRIMARY:
            self.refreshpass()
        elif pos == Gtk.EntryIconPosition.SECONDARY:
            newvis = not self.passentry.get_visibility()
            self.passentry.set_visibility(newvis)
            self.passentry.set_icon_tooltip_text(
                Gtk.EntryIconPosition.SECONDARY,
                "hide password" if newvis else "show password",
            )

    def passentry_popup(
        self, entry: Gtk.Entry, widget: Gtk.Widget, data: Optional[Any] = None
    ) -> None:
        self.add_to_menu(widget, "Generate a new password", self.refreshpass, 0)
        self.add_to_menu(
            widget,
            "Hide password" if self.passentry.get_visibility() else "Show password",
            lambda x: self.passentry_icon_clicked(
                widget, Gtk.EntryIconPosition.SECONDARY
            ),
            1,
        )
        sep = Gtk.SeparatorMenuItem()
        sep.show()
        widget.insert(sep, 2)

    def refreshpass(
        self, widget: Optional[Gtk.Widget] = None, event: Optional[Gdk.Event] = None
    ) -> None:
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
        Gtk.main_quit()

    def destroy(self, widget: Gtk.Widget, data: Optional[Any] = None) -> None:
        Gtk.main_quit()

    def returnValue(self) -> Optional[Dict[str, str]]:
        if self.selected is None:
            Gtk.main()
        return self.selected
