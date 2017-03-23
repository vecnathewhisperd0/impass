import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Gdk

############################################################

# Assumes that the func_data is set to the number of the text column in the
# model.
def _match_func(completion, key, iter, column):
    model = completion.get_model()
    text = model[iter][column]
    if text.lower().find(key.lower()) > -1:
        return True
    return False
_gui_layout = '''<?xml version="1.0" encoding="UTF-8"?>
<!-- Generated with glade 3.20.0 -->
<interface>
  <requires lib="gtk+" version="3.20"/>
  <object class="GtkWindow" id="assword-gui">
    <property name="can_focus">False</property>
    <property name="border_width">4</property>
    <property name="title" translatable="yes">assword</property>
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
                <property name="label" translatable="yes">WARNING: could not validate signature on db file!</property>
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
            <property name="label">Global state of assword gui</property>
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
                <property name="placeholder_text" translatable="yes">Enter context…</property>
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
          </object>
          <packing>
            <property name="expand">False</property>
            <property name="fill">True</property>
            <property name="position">2</property>
          </packing>
        </child>
      </object>
    </child>
  </object>
</interface>
'''

class Gui:
    """Assword X-based query UI."""
    def __init__(self, db, query=None):
        '''
+--------------------- warning --------------------+
|                    notification                  |
+--------------------------------------------------+
|                    description                   |
+----------------- simplebox ----------------------+
| [_simplectxentry___________________] <simplebtn> |
+--------------------------------------------------+
'''
        self.db = db
        self.query = None
        self.results = None
        self.selected = None
        self.window = None
        self.entry = None
        self.label = None
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

        self.builder = Gtk.Builder.new_from_string(_gui_layout, len(_gui_layout))
        self.window = self.builder.get_object('assword-gui')
        self.entry = self.builder.get_object('simplectxentry')
        self.simplebtn = self.builder.get_object('simplebtn')
        self.warning = self.builder.get_object('warning')

        if self.db.sigvalid is False:
            self.warning.show()
        
        completion = Gtk.EntryCompletion()
        self.entry.set_completion(completion)
        liststore = Gtk.ListStore(GObject.TYPE_STRING)
        completion.set_model(liststore)
        completion.set_text_column(0)
        completion.set_match_func(_match_func, 0) # 0 is column number
        context_len = 50
        for context in sorted(filter(lambda x: x == x.strip(), self.db), key=str.lower):
            if len(context) > context_len:
                context_len = len(context)
            liststore.append([context])
        self.window.connect("destroy", self.destroy)
        self.window.connect("key-press-event", self.keypress)
        self.entry.connect("activate", self.simpleclicked)
        self.entry.connect("changed", self.update_simple_context_entry)
        self.simplebtn.connect("clicked", self.simpleclicked)

        if query:
            self.entry.set_text(query)
        self.set_state('Enter context for desired password:')
        self.update_simple_context_entry(None)
        self.window.show()

    def set_state(self, state):
        self.builder.get_object('description').set_label(state)
        
    def update_simple_context_entry(self, widget):
        sctx = self.entry.get_text().strip()

        if sctx in self.db:
            self.simplebtn.set_label("Emit")
            self.simplebtn.set_sensitive(True)
        elif sctx is None or sctx == '':
            self.simplebtn.set_label("Emit")
            self.simplebtn.set_sensitive(False)
        else:
            self.simplebtn.set_label("Create")
            self.simplebtn.set_sensitive(True)

    def simpleclicked(self, widget):
        sctx = self.entry.get_text().strip()
        if sctx in self.db:
            self.retrieve(None)
        elif sctx is None or sctx == '':
            pass
        else:
            self.create(None)
        
    def keypress(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()

    def retrieve(self, widget, data=None):
        sctx = self.entry.get_text().strip()
        if sctx in self.db:
            self.selected = self.db[sctx]
            if self.selected is None:
                self.label.set_text("weird -- no context found even though we thought there should be one")
            else:
                Gtk.main_quit()
        else:
            self.label.set_text("no match")

    def create(self, widget, data=None):
        sctx = self.entry.get_text().strip()
        self.selected = self.db.add(sctx)
        self.db.save()
        Gtk.main_quit()

    def destroy(self, widget, data=None):
        Gtk.main_quit()

    def returnValue(self):
        if self.selected is None:
            Gtk.main()
        return self.selected
