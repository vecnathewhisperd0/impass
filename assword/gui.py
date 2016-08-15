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

class Gui:
    """Assword X-based query UI."""
    def __init__(self, db, query=None):

        self.db = db
        self.query = None
        self.results = None
        self.selected = None
        self.window = None
        self.entry = None
        self.label = None

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

        self.window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        self.window.set_border_width(4)
        windowicon = self.window.render_icon(Gtk.STOCK_DIALOG_AUTHENTICATION, Gtk.IconSize.DIALOG)
        self.window.set_icon(windowicon)

        self.entry = Gtk.Entry()
        if query:
            self.entry.set_text(query)
        completion = Gtk.EntryCompletion()
        self.entry.set_completion(completion)
        liststore = Gtk.ListStore(GObject.TYPE_STRING)
        completion.set_model(liststore)
        completion.set_text_column(0)
        completion.set_match_func(_match_func, 0) # 0 is column number
        context_len = 50
        for context in sorted(self.db, key=str.lower):
            if len(context) > context_len:
                context_len = len(context)
            liststore.append([context])
        hbox = Gtk.HBox()
        vbox = Gtk.VBox()
        self.button = Gtk.Button("Create")
        self.label = Gtk.Label(label="enter context for desired password:")
        self.window.add(vbox)

        if self.db.sigvalid is False:
            notification = Gtk.Label()
            msg = "WARNING: could not validate signature on db file"
            notification.set_markup('<span foreground="red">%s</span>' % msg)
            if len(msg) > context_len:
                context_len = len(msg)
            hsep = Gtk.HSeparator()
            vbox.add(notification)
            vbox.add(hsep)
            notification.show()
            hsep.show()

        vbox.add(self.label)
        vbox.pack_end(hbox, False, False, 0)
        hbox.add(self.entry)
        hbox.pack_end(self.button, False, False, 0)
        self.entry.set_width_chars(context_len)
        self.entry.connect("activate", self.retrieve)
        self.entry.connect("changed", self.update_button)
        self.button.connect("clicked", self.create)
        self.window.connect("destroy", self.destroy)
        self.window.connect("key-press-event", self.keypress)
    
        self.entry.show()
        self.label.show()
        vbox.show()
        hbox.show()
        self.button.show()
        self.update_button(self.entry)
        self.window.show()

    def keypress(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()

    def update_button(self, widget, data=None):
        e = self.entry.get_text()
        self.button.set_sensitive(e != '' and e not in self.db)

    def retrieve(self, widget, data=None):
        e = self.entry.get_text()
        if e in self.db:
            self.selected = self.db[e]
            if self.selected is None:
                self.label.set_text("weird -- no context found even though we thought there should be one")
            else:
                Gtk.main_quit()
        else:
            self.label.set_text("no match")

    def create(self, widget, data=None):
        e = self.entry.get_text()
        self.selected = self.db.add(e)
        self.db.save()
        Gtk.main_quit()

    def destroy(self, widget, data=None):
        Gtk.main_quit()

    def returnValue(self):
        if self.selected is None:
            Gtk.main()
        return self.selected
