"""S12: page audits read server-rendered PHP views without template noise.

Bug: accessibility, SEO, GEO and UX only read .html/.jsx/.tsx (and .vue,
.svelte, .css for UX), so the real pages of a PHP/CodeIgniter project were
never audited. Reading them naively would produce a new wave of false
positives: ``<img src="<?= $x ?>">`` ends the tag at the ``>`` of ``?>``,
``alt="<?= $alt ?>"`` looks empty, and partial views have no <html>/<title>.

Fix: ``.php``/``.phtml`` files are views only when markup remains after their
PHP blocks are masked with ``{...}``; document-level checks run only on files
that contain the element (partials never trigger them); error and e-mail
templates are not SEO/GEO pages.
"""
from __future__ import annotations

import unittest

from audit_helpers import TempProject, load_audit, run_main

common = load_audit("audit_common")
a11y = load_audit("accessibility_checker")
seo = load_audit("seo_checker")
geo = load_audit("geo_checker")
ux_audit = load_audit("ux_audit")

CONTROLLER = "<?php\n\nnamespace App\\Controllers;\n\nclass Home extends BaseController\n{\n    public function index(): string\n    {\n        return view('home', ['title' => 'Home']);\n    }\n}\n"
LAYOUT = """<!doctype html>
<html lang="<?= service('request')->getLocale() ?>">
<head>
  <title><?= esc($title) ?></title>
  <meta name="description" content="<?= esc($description ?? '') ?>">
  <meta property="og:title" content="<?= esc($title) ?>">
</head>
<body>
  <a class="skip-link" href="#conteudo">Pular para o conteudo</a>
  <header><nav><a href="<?= site_url('/') ?>">Inicio</a></nav></header>
  <main id="conteudo"><?= $this->renderSection('content') ?></main>
</body>
</html>
"""
VIEW = """<?= $this->extend('layouts/main') ?>
<?= $this->section('content') ?>
<h1><?= esc($title) ?></h1>
<?php if ($items): ?>
  <ul><?php foreach ($items as $item): ?><li><?= esc($item['name']) ?></li><?php endforeach ?></ul>
<?php endif ?>
<img src="<?= base_url('img/logo.png') ?>" alt="<?= esc($alt) ?>">
<form method="post" action="<?= site_url('contato') ?>">
  <?= csrf_field() ?>
  <label for="email">E-mail</label>
  <input type="email" id="email" name="email" value="<?= old('email') ?>">
  <input type="submit" value="Enviar">
  <button type="submit"><?= lang('App.send') ?></button>
</form>
<?= $this->endSection() ?>
"""
PARTIAL = '<nav class="menu"><a href="<?= site_url(\'/\') ?>">Inicio</a></nav>\n'
BROKEN_VIEW = '<h1>Produtos</h1>\n<img src="<?= base_url(\'a.png\') ?>">\n<button><i class="icon"></i></button>\n<div onclick="go()">Abrir</div>\n'
ERROR_PAGE = "<!doctype html><html><head><title>404</title></head><body><h1>404</h1><p><?= esc($message) ?></p></body></html>\n"


def seed_codeigniter(project) -> None:
    project.write("app/Controllers/Home.php", CONTROLLER)
    project.write("app/Config/App.php", "<?php\n$config['x'] = '<b>';\n")
    project.write("app/Views/layouts/main.php", LAYOUT)
    project.write("app/Views/home.php", VIEW)
    project.write("app/Views/partials/_nav.php", PARTIAL)
    project.write("app/Views/errors/html/error_404.php", ERROR_PAGE)


class TestMaskServerCode(unittest.TestCase):
    def test_blocks_become_markers_and_lines_are_kept(self):
        source = "<p><?php\n// a ?> b\n</p>\n<a href=\"<?= '?>' ?>\">x</a>\n<?php echo <<<EOT\n?> inside\nEOT;\n?><i>"
        masked = common.mask_server_code(source)
        self.assertEqual(masked.count("\n"), source.count("\n"))
        self.assertNotIn("?>", masked)
        self.assertIn(" b\n", masked)  # a // comment ends at ?>, as in PHP
        self.assertIn('<a href="{...}">x</a>', masked)  # "?>" inside a string does not close the block
        self.assertTrue(masked.endswith("<i>"))

    def test_pure_php_is_not_a_view(self):
        with TempProject() as project:
            seed_codeigniter(project)
            self.assertIsNone(common.read_markup_source(project.root / "app/Controllers/Home.php"))
            self.assertIsNone(common.read_markup_source(project.root / "app/Config/App.php"))
            self.assertIsNotNone(common.read_markup_source(project.root / "app/Views/partials/_nav.php"))


class TestAccessibilityOnPhpViews(unittest.TestCase):
    def test_codeigniter_views_have_no_template_false_positives(self):
        with TempProject() as project:
            seed_codeigniter(project)
            files = sorted(p.relative_to(project.root).as_posix() for p in a11y.find_html_files(project.root))
            issues = {name: a11y.check_accessibility(project.root / name) for name in files}
        self.assertNotIn("app/Controllers/Home.php", files)
        self.assertNotIn("app/Config/App.php", files)
        self.assertIn("app/Views/home.php", files)
        for name in ("app/Views/home.php", "app/Views/layouts/main.php", "app/Views/partials/_nav.php"):
            self.assertEqual(issues[name], [], name)

    def test_real_problems_in_php_views_are_still_found(self):
        with TempProject() as project:
            project.write("app/Views/produtos.php", BROKEN_VIEW)
            issues = a11y.check_accessibility(project.root / "app/Views/produtos.php")
            code, out = run_main(a11y, [str(project.root)])
        self.assertIn("Non-interactive element with onClick lacks role, tabIndex, or keyboard handler", issues)
        self.assertEqual(code, 1, out)
        self.assertIn("app/Views/produtos.php", out)


class TestSeoOnPhpViews(unittest.TestCase):
    def test_layout_head_checked_partials_and_error_pages_skipped(self):
        with TempProject() as project:
            seed_codeigniter(project)
            pages = sorted(p.relative_to(project.root).as_posix() for p in seo.find_pages(project.root))
            results = {name: seo.check_page(project.root / name, project.root)["issues"] for name in pages}
        self.assertEqual(pages, ["app/Views/home.php", "app/Views/layouts/main.php", "app/Views/partials/_nav.php"])
        self.assertEqual(results, {name: [] for name in pages})

    def test_missing_alt_in_php_view_is_reported(self):
        self.assertIn("Image missing alt attribute", seo.check_content(common.mask_server_code(BROKEN_VIEW)))


class TestGeoOnPhpViews(unittest.TestCase):
    def test_only_content_views_are_pages(self):
        with TempProject() as project:
            seed_codeigniter(project)
            project.write("app/Views/sobre.php", "<h1>Sobre</h1><h2>A</h2><h2>B</h2>\n")
            pages = sorted(p.relative_to(project.root).as_posix() for p in geo.find_web_pages(project.root))
            result = geo.check_page(project.root / "app/Views/home.php", project.root)
        self.assertEqual(pages, ["app/Views/home.php", "app/Views/sobre.php"])
        self.assertIn("Single H1 heading (clear topic)", result["passed"])


class TestUxOnPhpViews(unittest.TestCase):
    def test_views_audited_controllers_ignored(self):
        with TempProject() as project:
            seed_codeigniter(project)
            auditor = ux_audit.UXAuditor()
            auditor.audit_directory(str(project.root))
        self.assertEqual(auditor.files_checked, 4)  # layout, home, partial, error page; no controller/config
        self.assertFalse(any("Missing img alt text" in issue for issue in auditor.issues), auditor.issues)

    def test_only_php_without_markup_is_skipped(self):
        with TempProject() as project:
            project.write("app/Controllers/Home.php", CONTROLLER)
            code, out = run_main(ux_audit, [str(project.root)])
        self.assertEqual(code, 3, out)


if __name__ == "__main__":
    unittest.main()
