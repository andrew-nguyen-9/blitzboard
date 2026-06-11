// Inline, render-blocking script that sets data-theme BEFORE first paint to
// avoid a flash of the wrong theme. Reads saved preference or falls back to
// the OS setting ("system"). Kept dependency-free on purpose.
export default function ThemeScript() {
  const code = `(function(){try{
    var p = localStorage.getItem('ffdt-theme') || 'system';
    var sys = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', p === 'system' ? sys : p);
    document.documentElement.setAttribute('data-theme-pref', p);
  }catch(e){document.documentElement.setAttribute('data-theme','dark');}})();`;
  return <script dangerouslySetInnerHTML={{ __html: code }} />;
}
