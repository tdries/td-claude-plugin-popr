// POPR confetti overlay.
//
//   osascript -l JavaScript overlay.js <gif> <seconds> <size>
//
// Draws a borderless, transparent, click-through window that plays the confetti
// burst, then closes. macOS renders notification banners itself and will not
// animate anything in them, so the only way to get motion is to stop asking the
// notification system for it and draw our own window.
//
// JXA's ObjC bridge rather than Swift: osascript ships with macOS, so this needs
// no Xcode, no toolchain and no extra dependency at install time.
ObjC.import('AppKit');
ObjC.import('Foundation');

function run(argv) {
    var gif = argv[0];
    var seconds = parseFloat(argv[1] || '1.3');
    var size = parseInt(argv[2] || '180', 10);

    var img = $.NSImage.alloc.initWithContentsOfFile(gif);
    if (!img.js) { return 'popr: could not load ' + gif; }

    // Accessory: no Dock icon, and it never takes focus from what you are doing.
    $.NSApplication.sharedApplication.setActivationPolicy(2);

    // visibleFrame excludes the menu bar and Dock, so the burst lands in the
    // same top-right corner the banner does.
    var vf = $.NSScreen.mainScreen.visibleFrame;
    var frame = $.NSMakeRect(
        vf.origin.x + vf.size.width - size - 24,
        vf.origin.y + vf.size.height - size - 24,
        size, size);

    var win = $.NSWindow.alloc.initWithContentRectStyleMaskBackingDefer(
        frame, 0 /* borderless */, 2 /* buffered */, false);
    win.setOpaque(false);
    win.setBackgroundColor($.NSColor.clearColor);
    win.setLevel(25);                  // status level, above ordinary windows
    win.setIgnoresMouseEvents(true);   // clicks pass straight through to whatever is under it
    win.setHasShadow(false);
    win.setCollectionBehavior(1 | 16); // every Space, and does not slide when you switch

    var view = $.NSImageView.alloc.initWithFrame($.NSMakeRect(0, 0, size, size));
    view.setImage(img);
    view.setAnimates(true);
    view.setImageScaling(3);           // proportionally up or down
    win.setContentView(view);
    win.orderFrontRegardless;

    $.NSRunLoop.currentRunLoop.runUntilDate(
        $.NSDate.dateWithTimeIntervalSinceNow(seconds));
    win.close;
    return 'ok';
}
