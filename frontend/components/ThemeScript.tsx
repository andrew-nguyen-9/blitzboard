// Inline, render-blocking script that sets data-theme BEFORE first paint to
// avoid a flash of the wrong theme. Default is dark; only an explicit 'light'
// preference opts out. Legacy 'system'/'auto' coerce to dark. Dependency-free.
export default function ThemeScript() {
  const code = `(function(){try{
    var d = document.documentElement, ls = localStorage;
    var p = ls.getItem('ffdt-theme') === 'light' ? 'light' : 'dark';
    d.setAttribute('data-theme', p);
    d.setAttribute('data-theme-pref', p);
    // restore a11y preferences (see A11ySettings) before first paint
    var ts = ls.getItem('ffdt-a11y-type-scale'); if(ts) d.setAttribute('data-type-scale', ts);
    if(ls.getItem('ffdt-a11y-motion') === 'reduce') d.setAttribute('data-motion','reduce');
    if(ls.getItem('ffdt-a11y-contrast') === 'high') d.setAttribute('data-contrast','high');
    var cvd = ls.getItem('ffdt-a11y-cvd'); if(cvd && cvd !== 'none') d.setAttribute('data-cvd', cvd);
  }catch(e){document.documentElement.setAttribute('data-theme','dark');}})();`;
  return <script dangerouslySetInnerHTML={{ __html: code }} />;
}
