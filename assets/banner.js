// POPR banner: drawn by us, not by macOS.
//
//   osascript -l JavaScript banner.js <title> <message> <icon> <slot> <style> <click> <maxSeconds> <font> <dna> <burstSize>
//
// style is 'pill' (ivory) or 'glass' (a real blur of what is behind it).
//
// macOS gives no control over a notification banner. The layout is fixed, the
// icon comes from the app bundle and cannot be emptied (an empty icns renders a
// white square, tested on a bundle id it had never seen), and nothing in it will
// animate. So POPR draws its own window. That also means we know exactly where
// it is, which is what lets the confetti land on it.
//
// Two JXA hazards worth knowing, both learned the hard way:
//   · `someNSColor.CGColor` hands back a pointer owned by a temporary. The first
//     use survives by luck, the second crashes the process with no error at all.
//     So this file never touches CGColor: NSBox takes NSColor directly.
//   · A borderless window that accepts clicks would normally activate the app.
//     A non-activating NSPanel takes the click and leaves your focus alone.
ObjC.import('AppKit');
ObjC.import('Foundation');
ObjC.import('CoreFoundation');

var PITCH = 40;      // vertical distance between stacked banners

// NSTextField puts a single line slightly above the centre of its frame, so a
// small correction remains even with a plain container. Measured from rendered
// pixels, not reasoned about.
//
// MARK_NUDGE shifts the confetti right of the pill's left padding. Dead-equal
// margins looked cramped against a rounded edge: the curve eats into the corner,
// so the mark reads as closer to the border than it measures.
var TEXT_NUDGE = -3;
var MARK_NUDGE = 3;
var state = { clicked: false };

// The burst is drawn here rather than played from a GIF, which is what lets
// every project have its own. Colours are POPR's explosion palette.
var BURST_COLOURS = ['#C15F3C', '#FFFFFF', '#F4F3EE', '#B1ADA1'];

// The mark uses the Anthropic set rather than the burst's. Two of the burst
// colours are white and off-white, which are invisible against an ivory banner;
// out on the desktop they are the sparkle.
var MARK_COLOURS = ['#D97757', '#CC785C', '#BF9C88', '#6A9BCC', '#BCD1CA', '#CBCADB'];
// Every burst carries all four colours, twice each, so no project draws a dull
// one by chance and they all have the same weight on screen.
var BURST_PER_COLOUR = 2;
var BURST_SECONDS = 0.95;

// FNV-1a, so a project slug always produces the same confetti. Its arrangement
// is that project's signature: you learn to recognise which one finished
// without reading a word.
function seedOf(str) {
    var h = 2166136261;
    for (var i = 0; i < str.length; i++) {
        h ^= str.charCodeAt(i);
        h = Math.imul(h, 16777619);
    }
    return h >>> 0;
}

function rngFrom(seed) {
    return function () {                       // mulberry32
        seed = (seed + 0x6D2B79F5) >>> 0;
        var t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

// The logo is drawn per project too, from the same DNA as the burst but a
// different stream, so a project's mark and its explosion are siblings rather
// than the same arrangement twice. Chips are laid on a 4x4 grid so they never
// collide and still read as pixel confetti at 20px.
//
// Every mark carries every colour exactly once: same count, same palette, only
// the arrangement differs. That keeps marks comparable at a glance instead of
// one project looking busier than another.
function markFor(dna, size) {
    var rand = rngFrom(seedOf(dna) ^ 0x9E3779B9);

    // Chips live inside a margin, never edge to edge, so the mark keeps clear of
    // the pill's border however the arrangement falls.
    var MARGIN = 2;
    var g = 3, inner = size - MARGIN * 2, cell = inner / g;

    // Two chips per row, always. Balancing vertically by construction beats
    // fixing it afterwards: a shift big enough to correct a lopsided draw is
    // also big enough to push a chip out of the icon.
    var palette = shuffled(MARK_COLOURS, rand), chips = [], row, i = 0;
    for (row = 0; row < g; row++) {
        var cols = shuffled([0, 1, 2], rand).slice(0, 2);
        for (var c = 0; c < cols.length; c++) {
            var s = Math.max(3, Math.round(cell * (0.72 + rand() * 0.4)));
            chips.push({
                x: MARGIN + cols[c] * cell + (cell - s) / 2,
                y: MARGIN + row * cell + (cell - s) / 2,
                size: s,
                colour: palette[i++],
            });
        }
    }

    // A small correction for the horizontal draw, which is still random, and for
    // the size jitter. Clamped, because with the rows balanced it only ever has
    // a fraction of a pixel to do and the margin can absorb it.
    var weight = 0, mx = 0, my = 0;
    for (i = 0; i < chips.length; i++) {
        var a = chips[i].size * chips[i].size;
        weight += a;
        mx += (chips[i].x + chips[i].size / 2) * a;
        my += (chips[i].y + chips[i].size / 2) * a;
    }
    var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (i = 0; i < chips.length; i++) {
        minX = Math.min(minX, chips[i].x);
        minY = Math.min(minY, chips[i].y);
        maxX = Math.max(maxX, chips[i].x + chips[i].size);
        maxY = Math.max(maxY, chips[i].y + chips[i].size);
    }
    var dx = Math.max(-minX, Math.min(size / 2 - mx / weight, size - maxX));
    var dy = Math.max(-minY, Math.min(size / 2 - my / weight, size - maxY));

    for (i = 0; i < chips.length; i++) {
        chips[i].x = Math.round(chips[i].x + dx);
        chips[i].y = Math.round(chips[i].y + dy);
    }
    return chips;
}

function screenUnderPointer() {
    var mouse = $.NSEvent.mouseLocation;
    var screens = $.NSScreen.screens;
    for (var i = 0; i < screens.count; i++) {
        var s = screens.objectAtIndex(i), f = s.frame;
        if (mouse.x >= f.origin.x && mouse.x < f.origin.x + f.size.width &&
            mouse.y >= f.origin.y && mouse.y < f.origin.y + f.size.height) {
            return s;
        }
    }
    return $.NSScreen.mainScreen;
}

function shuffled(list, rand) {
    var a = list.slice(), i, j, swap;
    for (i = a.length - 1; i > 0; i--) {
        j = Math.floor(rand() * (i + 1));
        swap = a[i]; a[i] = a[j]; a[j] = swap;
    }
    return a;
}

function chipsFor(dna, reach) {
    var rand = rngFrom(seedOf(dna)), palette = [], i;
    for (i = 0; i < BURST_PER_COLOUR; i++) { palette = palette.concat(BURST_COLOURS); }
    palette = shuffled(palette, rand);

    var chips = [];
    for (i = 0; i < palette.length; i++) {
        chips.push({
            angle: (i / palette.length) * Math.PI * 2 + (rand() - 0.5) * 0.9,
            distance: reach * (0.45 + rand() * 0.55),
            size: Math.round(reach * (0.16 + rand() * 0.14)),
            colour: palette[i],
            lead: rand() * 0.12,
        });
    }
    return chips;
}

ObjC.registerSubclass({
    name: 'PoprClickCatcher',
    superclass: 'NSView',
    methods: {
        'mouseDown:': {
            types: ['void', ['id']],
            implementation: function () {
                state.clicked = true;
                // Break the run loop immediately rather than waiting for the
                // next poll, so dismissal is instant however lazily we tick.
                $.CFRunLoopStop($.CFRunLoopGetCurrent);
            },
        },
    },
});

function hex(h, a) {
    h = h.replace('#', '');
    return $.NSColor.colorWithSRGBRedGreenBlueAlpha(
        parseInt(h.substr(0, 2), 16) / 255,
        parseInt(h.substr(2, 2), 16) / 255,
        parseInt(h.substr(4, 2), 16) / 255, a === undefined ? 1 : a);
}

function box(x, y, w, h, fill, radius, borderColour) {
    var b = $.NSBox.alloc.initWithFrame($.NSMakeRect(x, y, w, h));
    b.setBoxType(4);        // custom
    b.setTitlePosition(0);  // no title
    b.setFillColor(fill);
    b.setCornerRadius(radius || 0);
    if (borderColour) {
        b.setBorderColor(borderColour);
        b.setBorderWidth(1);
    } else {
        b.setBorderWidth(0);
    }
    return b;
}

// Anthropic's own faces are Styrene and Tiempos, both licensed commercial fonts
// that cannot ship with an open source package. Use them when the machine has
// them, fall back to the system font, which is what Claude's interface does too.
function font(size, family) {
    if (family) {
        var f = $.NSFont.fontWithNameSize(family, size);
        if (!f.isNil()) { return f; }
    }
    return $.NSFont.systemFontOfSizeWeight(size, 0.0); // regular, never bold
}

// One line, always. The caller trims the text on a word boundary beforehand, so
// clipping here should never actually bite; it is a backstop, and it clips
// rather than adding an ellipsis because the ellipsis was explicitly unwanted.
function label(text, size, colour, w, family) {
    var f = $.NSTextField.alloc.initWithFrame($.NSMakeRect(0, 0, w, size + 7));
    f.setStringValue(text);
    f.setFont(font(size, family));
    f.setTextColor(colour);
    f.setBezeled(false);
    f.setDrawsBackground(false);
    f.setEditable(false);
    f.setSelectable(false);
    f.setUsesSingleLineMode(true);
    f.cell.setWraps(false);
    f.cell.setLineBreakMode($.NSLineBreakByClipping);
    // Ask the field how tall it actually is rather than guessing from the point
    // size. A guess leaves slack inside the frame, and centring a frame with
    // slack in it does not centre the text you can see.
    var need = f.fittingSize;
    f.setFrame($.NSMakeRect(0, 0, w, Math.ceil(need.height)));
    return f;
}

function run(argv) {
  try {
    var title = argv[0] || 'POPR';
    var message = argv[1] || '';
    var iconPath = argv[2] || '';
    var slot = parseInt(argv[3] || '0', 10);
    var style = argv[4] || 'pill';   // pill (ivory) or glass (blurred dark)
    var clickCmd = argv[5] || '';
    var maxSeconds = parseFloat(argv[6] || '600');
    var family = argv[7] || '';   // e.g. "Styrene A" when the machine has it
    var dna = argv[8] || '';                       // project slug; '' means no burst
    var burstSize = parseInt(argv[9] || '90', 10);

    $.NSApplication.sharedApplication.setActivationPolicy(2);

    var dark = style === 'glass';
    // One line, always. Half the height it used to be: a status bar, not a card.
    // PAD and ICON are tied: for the mark to sit an equal distance from the
    // pill's edge on every side, its inset from the left must match the gap
    // above and below it, which is (H - ICON) / 2. 7 and 16 satisfy that at 30.
    var W = 470, H = 30, PAD = 7, GAP = 9, ICON = 16;

    var ivory = hex('#F0EEE6', 0.98);
    var hairline = hex('#191919', 0.10);
    // Grey rather than black. A banner is a glance, not a headline: near-black
    // on ivory shouts, and this sits on the page instead of on top of it.
    var textColour = dark ? hex('#FFFFFF', 0.72) : hex('#6B6862');

    var img = null;
    if (iconPath) {
        var candidate = $.NSImage.alloc.initWithContentsOfFile(iconPath);
        if (candidate.js) { img = candidate; }
    }

    // Lay the text out FIRST: its height decides the banner's, so nothing is
    // ever cut off, however long Claude's last sentence happened to be.
    var textX = (img || dna) ? PAD + ICON + GAP : PAD;
    var textW = W - textX - PAD;
    var line = message ? title + '   ' + message : title;
    var field = label(line, 9.6, textColour, textW, family);   // 20% down from 12

    // The screen the pointer is on, not "main". On a two screen desk the main
    // screen is wherever the menu bar lives, which is regularly not the one you
    // are looking at, and a banner you never see is worse than no banner.
    var vf = screenUnderPointer().visibleFrame;
    var x = vf.origin.x + vf.size.width - W - 20;
    var y = vf.origin.y + vf.size.height - H - 14 - slot * PITCH;

    // Non-activating panel: it can be clicked without stealing your focus.
    var win = $.NSPanel.alloc.initWithContentRectStyleMaskBackingDefer(
        $.NSMakeRect(x + 28, y, W, H), 128, 2, false);
    win.setOpaque(false);
    win.setBackgroundColor($.NSColor.clearColor);
    win.setLevel(25);
    win.setHasShadow(true);
    win.setFloatingPanel(true);
    win.setBecomesKeyOnlyIfNeeded(true);
    win.setCollectionBehavior(1 | 16);
    win.setAlphaValue(0);

    // A plain view holds everything, with the background as its first subview.
    // Do not make the NSBox the root: addSubview on an NSBox goes into its
    // contentView, which NSBox insets by contentViewMargins, so every child ends
    // up shifted by an amount that never appears in any coordinate you wrote.
    var root = $.NSView.alloc.initWithFrame($.NSMakeRect(0, 0, W, H));
    if (dark) {
        var blur = $.NSVisualEffectView.alloc.initWithFrame($.NSMakeRect(0, 0, W, H));
        blur.setMaterial(13);     // HUD: a real blur of whatever is behind
        blur.setBlendingMode(0);
        blur.setState(1);         // stay active even though we never take focus
        blur.setWantsLayer(true);
        blur.layer.setCornerRadius(H / 2);
        blur.layer.setMasksToBounds(true);
        root.addSubview(blur);
    } else {
        root.addSubview(box(0, 0, W, H, ivory, H / 2, hairline));
    }

    if (img) {
        var iv = $.NSImageView.alloc.initWithFrame(
            $.NSMakeRect(PAD, (H - ICON) / 2, ICON, ICON));
        iv.setImage(img);
        iv.setImageScaling(3);
        root.addSubview(iv);
    } else if (dna) {
        var mark = $.NSView.alloc.initWithFrame(
            $.NSMakeRect(PAD + MARK_NUDGE, (H - ICON) / 2, ICON, ICON));
        var mc = markFor(dna, ICON);
        for (var mi = 0; mi < mc.length; mi++) {
            mark.addSubview(box(mc[mi].x, mc[mi].y, mc[mi].size, mc[mi].size,
                                hex(mc[mi].colour), 1, null));
        }
        root.addSubview(mark);
    }

    // A pixel below true centre. The field's measured box includes room for
    // descenders the caps never use, so dead-centre reads as sitting high.
    var fh = field.frame.size.height;
    field.setFrame($.NSMakeRect(textX, Math.round((H - fh) / 2) + TEXT_NUDGE, textW, fh));
    root.addSubview(field);

    // a transparent catcher on top, so a click anywhere on the banner counts
    root.addSubview($.PoprClickCatcher.alloc.initWithFrame($.NSMakeRect(0, 0, W, H)));

    win.setContentView(root);
    win.orderFrontRegardless;

    function tick(s) {
        $.NSRunLoop.currentRunLoop.runUntilDate($.NSDate.dateWithTimeIntervalSinceNow(s));
    }

    var i, n = 18;
    for (i = 1; i <= n; i++) {                      // slide in from the right, fading up
        var e = 1 - Math.pow(1 - i / n, 3);
        win.setAlphaValue(e);
        win.setFrameOrigin($.NSMakePoint(x + 28 * (1 - e), y));
        tick(0.010);
    }

    // The confetti comes out of the logo. This is only possible because we drew
    // the banner ourselves: macOS never reveals where it puts its own, so there
    // was nothing to aim at before.
    if (dna) {
        var reach = burstSize;
        var span = Math.ceil(reach * 2.6);
        var cx = x + PAD + ICON / 2;           // centre of the logo, in screen space
        var cy = y + H / 2;

        var bw = $.NSWindow.alloc.initWithContentRectStyleMaskBackingDefer(
            $.NSMakeRect(cx - span / 2, cy - span / 2, span, span), 0, 2, false);
        bw.setOpaque(false);
        bw.setBackgroundColor($.NSColor.clearColor);
        bw.setLevel(26);                       // just above the banner
        bw.setIgnoresMouseEvents(true);
        bw.setHasShadow(false);
        bw.setCollectionBehavior(1 | 16);

        var canvas = $.NSView.alloc.initWithFrame($.NSMakeRect(0, 0, span, span));
        var chips = chipsFor(dna, reach), boxes = [], ci;
        for (ci = 0; ci < chips.length; ci++) {
            var c = chips[ci];
            var bx = box(span / 2, span / 2, c.size, c.size, hex(c.colour), 1, null);
            canvas.addSubview(bx);
            boxes.push(bx);
        }
        bw.setContentView(canvas);
        bw.orderFrontRegardless;

        var steps = Math.round(BURST_SECONDS / 0.016);
        for (var st = 1; st <= steps; st++) {
            var pt = st / steps;
            for (ci = 0; ci < chips.length; ci++) {
                var ch = chips[ci];
                var lt = Math.max(0, Math.min(1, (pt - ch.lead) / (1 - ch.lead)));
                var out = 1 - Math.pow(1 - Math.min(lt / 0.45, 1), 3);   // thrown, then eased
                var fall = Math.pow(Math.max(0, lt - 0.45), 2) * reach * 2.2;
                boxes[ci].setFrameOrigin($.NSMakePoint(
                    span / 2 + Math.cos(ch.angle) * ch.distance * out - ch.size / 2,
                    span / 2 + Math.sin(ch.angle) * ch.distance * out - ch.size / 2 - fall));
            }
            bw.setAlphaValue(pt < 0.55 ? 1 : 1 - (pt - 0.55) / 0.45);
            tick(0.016);
        }
        bw.close;
    }

    // Stay put until clicked. maxSeconds is only a backstop so a forgotten
    // banner cannot leave a process running for the rest of the session.
    //
    // Waking twenty times a second to ask "clicked yet?" cost about 2% of a core
    // per open banner, which is absurd for a thing that is doing nothing. The
    // click handler stops the run loop itself, so this can idle in long blocks:
    // the wake is a backstop for the deadline, not the click.
    var waited = 0, CHUNK = 5;
    while (!state.clicked && waited < maxSeconds) {
        tick(Math.min(CHUNK, maxSeconds - waited));
        waited += CHUNK;
    }

    for (i = n; i >= 0; i--) { win.setAlphaValue(i / n); tick(0.008); }
    win.close;

    if (state.clicked && clickCmd) {
        var task = $.NSTask.alloc.init;
        task.setLaunchPath('/bin/sh');
        task.setArguments($(['-c', clickCmd]));
        task.launch;
        tick(0.25);
    }
    return state.clicked ? 'clicked' : 'timeout';
  } catch (e) {
    return 'popr banner error: ' + (e.message || e);
  }
}
