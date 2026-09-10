// Rules the generated marks and bursts must hold for every project name.
// Run by tests/test.sh through osascript, because this is JXA rather than node:
// it is the only way to exercise the same code the banner actually runs.
ObjC.import('AppKit');
ObjC.import('Foundation');

function run(argv) {
    var src = $.NSString.stringWithContentsOfFileEncodingError(
        argv[0], $.NSUTF8StringEncoding, null).js;
    eval(src.replace(/^function run\(argv\)[\s\S]*$/m, ''));   // definitions only

    var names = ['popr', 'acme-widgets', 'kikl-cockpit', 'biz-client-kikl',
                 'a', 'a-very-long-project-name-that-goes-on', 'Ünïcodé-Ñame', '123'];
    var failures = [], ICON = 16, REACH = 90;

    function check(cond, msg) { if (!cond) { failures.push(msg); } }

    names.forEach(function (name) {
        var m = markFor(name, ICON);
        check(m.length === MARK_COLOURS.length,
              name + ': mark has ' + m.length + ' chips, want ' + MARK_COLOURS.length);

        var seen = {};
        m.forEach(function (c) { seen[c.colour] = (seen[c.colour] || 0) + 1; });
        check(Object.keys(seen).length === MARK_COLOURS.length,
              name + ': mark uses ' + Object.keys(seen).length + ' colours, want all ' + MARK_COLOURS.length);
        MARK_COLOURS.forEach(function (col) {
            check(seen[col] === 1, name + ': mark uses ' + col + ' ' + (seen[col] || 0) + ' times, want once');
        });

        m.forEach(function (c) {
            check(c.x >= 0 && c.y >= 0 && c.x + c.size <= ICON && c.y + c.size <= ICON,
                  name + ': chip at ' + c.x + ',' + c.y + ' size ' + c.size + ' leaves the icon');
            check(c.size >= 3, name + ': chip of ' + c.size + 'px is too small to see');
        });

        // vertical mass within a pixel of centre, which is what "centred" means
        // to the eye when only six chips are in play
        var w = 0, my = 0;
        m.forEach(function (c) { var a = c.size * c.size; w += a; my += (c.y + c.size / 2) * a; });
        check(Math.abs(my / w - ICON / 2) <= 1.0,
              name + ': mark mass at y ' + (my / w).toFixed(2) + ', want ' + (ICON / 2) + ' +/- 1');

        var burst = chipsFor(name, REACH);
        check(burst.length === BURST_COLOURS.length * BURST_PER_COLOUR,
              name + ': burst has ' + burst.length + ' chips');
        var bseen = {};
        burst.forEach(function (c) { bseen[c.colour] = (bseen[c.colour] || 0) + 1; });
        BURST_COLOURS.forEach(function (col) {
            check(bseen[col] === BURST_PER_COLOUR,
                  name + ': burst uses ' + col + ' ' + (bseen[col] || 0) + ' times');
        });

        // the same name must always draw the same thing, or it is not a DNA
        check(JSON.stringify(markFor(name, ICON)) === JSON.stringify(m),
              name + ': mark is not deterministic');
        check(JSON.stringify(chipsFor(name, REACH)) === JSON.stringify(burst),
              name + ': burst is not deterministic');
    });

    // and different names must actually differ, or the DNA is decorative
    check(JSON.stringify(markFor('popr', ICON)) !== JSON.stringify(markFor('acme-widgets', ICON)),
          'two different projects produced identical marks');

    return failures.length ? 'FAIL\n  ' + failures.join('\n  ')
                           : 'ok (' + names.length + ' project names)';
}
