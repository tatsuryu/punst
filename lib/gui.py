import gi
gi.require_version('Gtk', '3.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, GObject, Pango, PangoCairo

from . import settings
from .utils import hex_to_rgb, format_text, NotificationUrgency


class NotificationDrawingArea(Gtk.DrawingArea):
    def __init__(self, *args, **kwargs):
        super(NotificationDrawingArea, self).__init__(*args, **kwargs)
        self.connect('draw', self.draw)
        self.text = ""
        self.urgency = NotificationUrgency.NORMAL

    def build_layout(self, cr):
        layout = PangoCairo.create_layout(cr)
        desc = Pango.FontDescription(settings.FONT)
        layout.set_font_description(desc)
        layout.set_width(Pango.SCALE * (
            settings.WIDTH -
            2 * (settings.PADDING[0] + settings.FRAME_WIDTH)
        ))
        layout.set_alignment(Pango.Alignment.LEFT)
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)
        if settings.USE_MARKUP:
            layout.set_markup(self.text, -1)
        else:
            layout.set_text(self.text, -1)
        return layout

    def position_window(self, width, height):
        screen = Gdk.Screen.get_default()
        monitor_rect = screen.get_monitor_geometry(settings.MONITOR_NUMBER)
        x = monitor_rect.x + settings.X
        if settings.X < 0:
            x += monitor_rect.width - width
        y = monitor_rect.y + settings.Y
        if settings.Y < 0:
            y += monitor_rect.height - height

        parent = self.get_parent_window()
        parent.resize(width, height)
        parent.move(x, y)

    def draw(self, widget, cr):
        layout = self.build_layout(cr)
        width = settings.WIDTH
        height = layout.get_pixel_size()[1] + 2 * (settings.PADDING[1] + settings.FRAME_WIDTH)

        bg_color = hex_to_rgb(settings.BG_COLORS[self.urgency])
        fg_color = hex_to_rgb(settings.FG_COLORS[self.urgency])
        if settings.FRAME_COLOR is None:
            frame_color = fg_color
        else:
            frame_color = hex_to_rgb(settings.FRAME_COLOR)

        cr.set_source_rgb(*bg_color)
        cr.rectangle(0, 0, width, height)
        cr.fill()
        cr.set_source_rgb(*frame_color)
        cr.rectangle(0, 0, width, height)
        cr.set_line_width(2 * settings.FRAME_WIDTH)
        cr.stroke()
        cr.set_source_rgb(*fg_color)
        cr.translate(*settings.PADDING)
        cr.translate(settings.FRAME_WIDTH, settings.FRAME_WIDTH)
        PangoCairo.update_layout(cr, layout)
        PangoCairo.show_layout(cr, layout)

        self.position_window(width, height)


class NotificationWindow(Gtk.Window):
    def __init__(self):
        super(NotificationWindow, self).__init__(type=Gtk.WindowType.POPUP)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_accept_focus(False)
        self.timeout = None
        self.drawing_area = NotificationDrawingArea()
        self.drawing_area.show()
        self.add(self.drawing_area)
        self.set_size_request(settings.WIDTH, -1)
        self.connect('button-release-event', self.on_click)

    def popup(self, summary, body, urgency):
        self.drawing_area.text = format_text(settings.FORMAT, summary, body)
        self.drawing_area.urgency = urgency
        self.queue_draw()
        self.show()
        if self.timeout:
            GObject.source_remove(self.timeout)
        timeout = settings.TIMEOUTS[urgency]
        if timeout is not None:
            self.timeout = GObject.timeout_add(timeout, self.remove)

    def remove(self):
        self.hide()
        if self.timeout:
            GObject.source_remove(self.timeout)
            self.timeout = None

    def on_click(self, event, data=None):
        self.remove()
