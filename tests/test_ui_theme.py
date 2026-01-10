#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI Theme Compatibility Tests

Tests to detect potential styling issues in light/dark themes.
Checks for:
1. Hardcoded colors that may cause black boxes
2. Missing theme-aware styling
3. Improper background/border handling
"""

import pytest
import re
import ast
from pathlib import Path


# Patterns that indicate potential theme issues
PROBLEMATIC_PATTERNS = {
    # Hardcoded dark colors in stylesheets
    'hardcoded_dark_bg': re.compile(
        r'background(?:-color)?:\s*#(?:2[0-9a-f]{5}|3[0-9a-f]{5}|1[0-9a-f]{5}|0[0-9a-f]{5})',
        re.IGNORECASE
    ),
    # Hardcoded light colors that won't work in dark theme
    'hardcoded_light_bg': re.compile(
        r'background(?:-color)?:\s*#(?:f[0-9a-f]{5}|e[0-9a-f]{5}|d[0-9a-f]{5}|white)',
        re.IGNORECASE
    ),
    # Hardcoded text colors
    'hardcoded_text_dark': re.compile(
        r'color:\s*#(?:0[0-9a-f]{5}|1[0-9a-f]{5}|2[0-9a-f]{5})',
        re.IGNORECASE
    ),
    'hardcoded_text_light': re.compile(
        r'color:\s*#(?:f[0-9a-f]{5}|e[0-9a-f]{5}|white)',
        re.IGNORECASE
    ),
    # Border with fixed colors (not transparent or none)
    'hardcoded_border': re.compile(
        r'border:\s*\d+px\s+\w+\s+#[0-9a-f]{3,6}',
        re.IGNORECASE
    ),
}

# Allowed patterns (theme-aware or transparent)
ALLOWED_PATTERNS = [
    r'background:\s*transparent',
    r'background-color:\s*transparent',
    r'border:\s*none',
    r'isDarkTheme\(\)',  # Using theme detection
    r'Theme\.',  # Using Theme enum
    r'setTheme\(',  # Setting theme
]

# Files that are known to need theme-aware styling
UI_FILES = [
    'UI/main_window.py',
    'UI/flash_page.py',
    'UI/erase_page.py',
    'UI/probe_page.py',
    'UI/chip_config_page.py',
    'UI/settings_page.py',
    'UI/help_page.py',
    'UI/log_widget.py',
    'UI/save_preset_dialog.py',
    'UI/probe/page.py',
]


def get_project_root() -> Path:
    """Get project root directory"""
    current = Path(__file__).parent.parent
    return current


def find_stylesheet_blocks(content: str) -> list:
    """
    Find all setStyleSheet calls and their content.
    Returns list of (line_number, stylesheet_content)
    """
    results = []
    lines = content.split('\n')
    
    in_stylesheet = False
    stylesheet_start = 0
    stylesheet_content = []
    paren_depth = 0
    triple_quote_active = False
    
    for i, line in enumerate(lines, 1):
        if 'setStyleSheet(' in line or 'setStyleSheet (' in line:
            in_stylesheet = True
            stylesheet_start = i
            stylesheet_content = [line]
            # Check for triple quotes
            if '"""' in line:
                count = line.count('"""')
                if count == 1:
                    triple_quote_active = True
                elif count >= 2:
                    # Both opening and closing on same line
                    triple_quote_active = False
            # Count parentheses
            paren_depth = line.count('(') - line.count(')')
            if paren_depth <= 0 and not triple_quote_active:
                results.append((stylesheet_start, '\n'.join(stylesheet_content)))
                in_stylesheet = False
                stylesheet_content = []
        elif in_stylesheet:
            stylesheet_content.append(line)
            if '"""' in line:
                count = line.count('"""')
                if triple_quote_active and count >= 1:
                    triple_quote_active = False
                elif not triple_quote_active and count == 1:
                    triple_quote_active = True
            paren_depth += line.count('(') - line.count(')')
            if paren_depth <= 0 and not triple_quote_active:
                results.append((stylesheet_start, '\n'.join(stylesheet_content)))
                in_stylesheet = False
                stylesheet_content = []
    
    return results


def is_in_theme_conditional(content: str, line_num: int) -> bool:
    """
    Check if a line is inside a theme conditional block (isDarkTheme() check).
    This includes both the if branch and the else branch of an isDarkTheme() check.
    """
    lines = content.split('\n')
    
    if line_num < 1 or line_num > len(lines):
        return False
    
    # Look backwards for isDarkTheme() or Theme. check
    indent_at_line = len(lines[line_num - 1]) - len(lines[line_num - 1].lstrip())
    
    # Track if we're in a theme-aware function
    in_theme_function = False
    
    for i in range(line_num - 1, max(0, line_num - 50), -1):
        line = lines[i]
        stripped = line.strip()
        
        if not stripped or stripped.startswith('#'):
            continue
            
        current_indent = len(line) - len(line.lstrip())
        
        # Check if we're inside a theme-related function
        if 'def _apply_theme' in line or 'def apply_theme' in line:
            return True
        
        # If we hit a line with less indentation
        if current_indent < indent_at_line:
            # Direct isDarkTheme check
            if 'isDarkTheme()' in line or 'if isDark' in line:
                return True
            
            # Check if we're in an else block that corresponds to isDarkTheme
            if stripped == 'else:':
                # Look backwards for the matching if with isDarkTheme
                else_indent = current_indent
                for j in range(i - 1, max(0, i - 30), -1):
                    prev_line = lines[j]
                    prev_stripped = prev_line.strip()
                    if not prev_stripped or prev_stripped.startswith('#'):
                        continue
                    prev_indent = len(prev_line) - len(prev_line.lstrip())
                    
                    # Found the if at the same indent level
                    if prev_indent == else_indent and prev_stripped.startswith('if'):
                        if 'isDarkTheme()' in prev_line:
                            return True
                        break
                    # Went past the matching if
                    if prev_indent < else_indent:
                        break
            
            # If we hit elif, check if any prior if has isDarkTheme
            if stripped.startswith('elif'):
                elif_indent = current_indent
                for j in range(i - 1, max(0, i - 30), -1):
                    prev_line = lines[j]
                    prev_stripped = prev_line.strip()
                    if not prev_stripped or prev_stripped.startswith('#'):
                        continue
                    prev_indent = len(prev_line) - len(prev_line.lstrip())
                    
                    if prev_indent == elif_indent and prev_stripped.startswith('if'):
                        if 'isDarkTheme()' in prev_line:
                            return True
                        break
                    if prev_indent < elif_indent:
                        break
            
            # Update indent tracking
            indent_at_line = current_indent
    
    return False


def check_file_for_theme_issues(filepath: Path) -> list:
    """
    Check a single file for potential theme compatibility issues.
    Returns list of (line_number, issue_description, code_snippet)
    """
    issues = []
    
    if not filepath.exists():
        return issues
    
    content = filepath.read_text(encoding='utf-8')
    stylesheet_blocks = find_stylesheet_blocks(content)
    
    for line_num, block in stylesheet_blocks:
        # Skip if inside a theme conditional
        if is_in_theme_conditional(content, line_num):
            continue
        
        # Check for allowed patterns first
        is_allowed = False
        for pattern in ALLOWED_PATTERNS:
            if re.search(pattern, block, re.IGNORECASE):
                is_allowed = True
                break
        
        if is_allowed:
            continue
        
        # Check for problematic patterns
        for issue_name, pattern in PROBLEMATIC_PATTERNS.items():
            matches = pattern.findall(block)
            if matches:
                # Extract first 100 chars of the block for context
                snippet = block[:150].replace('\n', ' ').strip()
                if len(block) > 150:
                    snippet += '...'
                issues.append((
                    line_num,
                    f"Potential theme issue ({issue_name}): {matches[0]}",
                    snippet
                ))
    
    return issues


class TestUIThemeCompatibility:
    """Test class for UI theme compatibility"""
    
    @pytest.fixture
    def project_root(self):
        return get_project_root()
    
    def test_save_preset_dialog_theme_handling(self, project_root):
        """Test that SavePresetDialog uses theme-aware styling"""
        filepath = project_root / 'UI' / 'save_preset_dialog.py'
        if not filepath.exists():
            pytest.skip("File not found")
        
        content = filepath.read_text(encoding='utf-8')
        
        # Should have isDarkTheme() check
        assert 'isDarkTheme()' in content or 'isDarkTheme' in content, \
            "SavePresetDialog should use isDarkTheme() for theme-aware styling"
        
        # Should have both light and dark theme handling
        assert '#2d2d2d' in content or 'dark' in content.lower(), \
            "Should have dark theme colors"
        assert '#ffffff' in content or '#fff' in content.lower() or 'white' in content.lower(), \
            "Should have light theme colors"
    
    def test_log_widget_no_hardcoded_colors(self, project_root):
        """Test that LogWidget doesn't have problematic hardcoded colors"""
        filepath = project_root / 'UI' / 'log_widget.py'
        if not filepath.exists():
            pytest.skip("File not found")
        
        issues = check_file_for_theme_issues(filepath)
        
        # Log widget stylesheet should only set font, not colors
        for line_num, issue, snippet in issues:
            # Allow font-related styling
            if 'font-family' in snippet or 'font-size' in snippet:
                continue
            # Fail on color issues
            if 'background' in issue.lower() or 'color' in issue.lower():
                pytest.fail(f"Line {line_num}: {issue}\nCode: {snippet}")
    
    def test_help_page_uses_transparent_background(self, project_root):
        """Test that HelpPage uses transparent backgrounds"""
        filepath = project_root / 'UI' / 'help_page.py'
        if not filepath.exists():
            pytest.skip("File not found")
        
        content = filepath.read_text(encoding='utf-8')
        
        # Should use transparent backgrounds
        assert 'transparent' in content, \
            "HelpPage should use transparent backgrounds for theme compatibility"
    
    def test_settings_page_uses_transparent_background(self, project_root):
        """Test that SettingsPage uses transparent backgrounds"""
        filepath = project_root / 'UI' / 'settings_page.py'
        if not filepath.exists():
            pytest.skip("File not found")
        
        content = filepath.read_text(encoding='utf-8')
        
        # Should use transparent backgrounds
        assert 'transparent' in content, \
            "SettingsPage should use transparent backgrounds"
    
    def test_no_unconditional_hardcoded_colors_in_dialogs(self, project_root):
        """Test that dialogs don't have unconditional hardcoded colors"""
        dialog_files = [
            'UI/save_preset_dialog.py',
        ]
        
        all_issues = []
        for rel_path in dialog_files:
            filepath = project_root / rel_path
            if filepath.exists():
                issues = check_file_for_theme_issues(filepath)
                if issues:
                    all_issues.extend([(rel_path, *issue) for issue in issues])
        
        # Note: This test documents issues but doesn't fail
        # because save_preset_dialog.py already has theme handling
        if all_issues:
            # Check if the issues are inside theme conditionals
            for rel_path, line_num, issue, snippet in all_issues:
                filepath = project_root / rel_path
                content = filepath.read_text(encoding='utf-8')
                if not is_in_theme_conditional(content, line_num):
                    pytest.fail(
                        f"{rel_path} line {line_num}: {issue}\n"
                        f"Code: {snippet}\n"
                        "Consider wrapping in isDarkTheme() conditional"
                    )
    
    def test_stylesheet_patterns_catalog(self, project_root):
        """Catalog all setStyleSheet usages for review"""
        ui_dir = project_root / 'UI'
        if not ui_dir.exists():
            pytest.skip("UI directory not found")
        
        all_stylesheets = []
        for py_file in ui_dir.rglob('*.py'):
            if py_file.name.startswith('__'):
                continue
            
            stylesheets = find_stylesheet_blocks(py_file.read_text(encoding='utf-8'))
            for line_num, content in stylesheets:
                all_stylesheets.append({
                    'file': str(py_file.relative_to(project_root)),
                    'line': line_num,
                    'content': content[:200]
                })
        
        # This test just catalogs - useful for manual review
        # Print summary if running with -v
        print(f"\nFound {len(all_stylesheets)} setStyleSheet calls:")
        for item in all_stylesheets:
            print(f"  {item['file']}:{item['line']}")
        
        assert len(all_stylesheets) >= 0  # Always passes, just for documentation


class TestSpecificThemeIssues:
    """Test specific known theme issues"""
    
    @pytest.fixture
    def project_root(self):
        return get_project_root()
    
    def test_qtext_edit_transparent_in_help_page(self, project_root):
        """Ensure QTextEdit in help_page uses transparent background"""
        filepath = project_root / 'UI' / 'help_page.py'
        if not filepath.exists():
            pytest.skip("File not found")
        
        content = filepath.read_text(encoding='utf-8')
        
        # Find QTextEdit stylesheet
        if 'QTextEdit' in content:
            # Should have transparent background
            assert 'background-color: transparent' in content or \
                   'background: transparent' in content, \
                "QTextEdit in help_page should use transparent background"
    
    def test_qdialog_styling_uses_theme_check(self, project_root):
        """Ensure QDialog styling checks theme"""
        filepath = project_root / 'UI' / 'save_preset_dialog.py'
        if not filepath.exists():
            pytest.skip("File not found")
        
        content = filepath.read_text(encoding='utf-8')
        
        # If setting QDialog background, should check theme first
        if 'QDialog' in content and 'background' in content:
            assert 'isDarkTheme' in content, \
                "QDialog background styling should check isDarkTheme()"
    
    def test_plaintext_edit_font_only(self, project_root):
        """Ensure PlainTextEdit only sets font, not colors"""
        filepath = project_root / 'UI' / 'log_widget.py'
        if not filepath.exists():
            pytest.skip("File not found")
        
        content = filepath.read_text(encoding='utf-8')
        stylesheets = find_stylesheet_blocks(content)
        
        for line_num, block in stylesheets:
            if 'PlainTextEdit' in block:
                # Should only have font settings
                lines = block.lower()
                if 'background' in lines and 'transparent' not in lines:
                    pytest.fail(
                        f"Line {line_num}: PlainTextEdit should not set background color\n"
                        f"Use transparent or let theme handle it"
                    )
                if 'color:' in lines and 'background-color' not in lines:
                    # Check if it's setting text color directly
                    if '#' in lines and 'font' not in lines:
                        pytest.fail(
                            f"Line {line_num}: PlainTextEdit should not set text color\n"
                            f"Let theme handle text colors"
                        )


class TestInfoBarMessageBoxUsage:
    """Test InfoBar and MessageBox usage for theme compatibility"""
    
    @pytest.fixture
    def project_root(self):
        return get_project_root()
    
    def test_infobar_has_parent(self, project_root):
        """Ensure InfoBar calls have parent parameter for proper theming"""
        ui_dir = project_root / 'UI'
        
        issues = []
        for py_file in ui_dir.rglob('*.py'):
            if py_file.name.startswith('__'):
                continue
            
            content = py_file.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                # Check for InfoBar.success/error/warning/info calls
                if re.search(r'InfoBar\.(success|error|warning|info)\s*\(', line):
                    # Should have parent= parameter
                    # Look at this line and next few lines for parent=
                    check_lines = '\n'.join(lines[i-1:i+5])
                    if 'parent=' not in check_lines and 'parent =' not in check_lines:
                        issues.append(f"{py_file.name}:{i}: InfoBar call may be missing parent parameter")
        
        if issues:
            # This is a warning, not a hard fail
            print("\nInfoBar calls that may need parent parameter:")
            for issue in issues:
                print(f"  {issue}")
    
    def test_messagebox_has_parent(self, project_root):
        """Ensure MessageBox calls have parent parameter"""
        ui_dir = project_root / 'UI'
        
        for py_file in ui_dir.rglob('*.py'):
            if py_file.name.startswith('__'):
                continue
            
            content = py_file.read_text(encoding='utf-8')
            
            # Find MessageBox instantiations
            matches = re.finditer(r'MessageBox\s*\(', content)
            for match in matches:
                # Get the full call (find matching parenthesis)
                start = match.start()
                paren_count = 0
                end = start
                for i, char in enumerate(content[start:], start):
                    if char == '(':
                        paren_count += 1
                    elif char == ')':
                        paren_count -= 1
                        if paren_count == 0:
                            end = i
                            break
                
                call_text = content[start:end+1]
                # MessageBox third argument should be parent
                # MessageBox(title, content, parent)
                args = call_text.split(',')
                if len(args) < 3:
                    line_num = content[:start].count('\n') + 1
                    pytest.fail(
                        f"{py_file.name}:{line_num}: MessageBox should have parent parameter\n"
                        f"Usage: MessageBox(title, content, parent)"
                    )


class TestQDialogThemeHandling:
    """Test that all QDialog subclasses have proper theme handling"""
    
    @pytest.fixture
    def project_root(self):
        return get_project_root()
    
    def test_all_dialogs_have_theme_handling(self, project_root):
        """Ensure all QDialog subclasses use isDarkTheme() for styling"""
        ui_dir = project_root / 'UI'
        
        dialogs_without_theme = []
        
        for py_file in ui_dir.rglob('*.py'):
            if py_file.name.startswith('__'):
                continue
            
            content = py_file.read_text(encoding='utf-8')
            
            # Find QDialog subclasses
            if 'class ' in content and '(QDialog)' in content:
                # This file has a QDialog subclass
                # Check if it uses isDarkTheme
                if 'isDarkTheme' not in content:
                    # Find the class name
                    match = re.search(r'class\s+(\w+)\s*\([^)]*QDialog[^)]*\)', content)
                    if match:
                        dialogs_without_theme.append(
                            f"{py_file.name}: {match.group(1)}"
                        )
        
        if dialogs_without_theme:
            pytest.fail(
                "The following QDialog subclasses do not have isDarkTheme() handling:\n" +
                "\n".join(f"  - {d}" for d in dialogs_without_theme) +
                "\n\nAdd _apply_theme_style() method with isDarkTheme() check"
            )
    
    def test_dialog_apply_theme_style_method(self, project_root):
        """Ensure dialogs with theme handling call _apply_theme_style in __init__"""
        ui_dir = project_root / 'UI'
        
        issues = []
        
        for py_file in ui_dir.rglob('*.py'):
            if py_file.name.startswith('__'):
                continue
            
            content = py_file.read_text(encoding='utf-8')
            
            # Only check files with QDialog subclasses
            if '(QDialog)' not in content:
                continue
            
            # Find classes with _apply_theme_style method
            if '_apply_theme_style' in content and 'def _apply_theme_style' in content:
                # Find all QDialog subclasses in this file
                class_matches = re.finditer(
                    r'class\s+(\w+)\s*\([^)]*QDialog[^)]*\):',
                    content
                )
                
                for class_match in class_matches:
                    class_name = class_match.group(1)
                    class_start = class_match.end()
                    
                    # Find the end of this class (next class or EOF)
                    next_class = re.search(r'\nclass\s+\w+', content[class_start:])
                    if next_class:
                        class_end = class_start + next_class.start()
                    else:
                        class_end = len(content)
                    
                    class_body = content[class_start:class_end]
                    
                    # Check if this class has _apply_theme_style
                    if 'def _apply_theme_style' not in class_body:
                        continue
                    
                    # Find __init__ in this class
                    init_match = re.search(
                        r'def __init__\s*\([^)]*\):(.*?)(?=\n    def |\Z)',
                        class_body, re.DOTALL
                    )
                    
                    if init_match:
                        init_body = init_match.group(1)
                        if '_apply_theme_style' not in init_body:
                            issues.append(
                                f"{py_file.name}: {class_name} has _apply_theme_style "
                                f"but doesn't call it in __init__"
                            )
        
        if issues:
            pytest.fail(
                "Theme style method not called in __init__:\n" +
                "\n".join(f"  - {i}" for i in issues)
            )


class TestGlobalThemeHandling:
    """Test global theme handling in main window"""
    
    @pytest.fixture
    def project_root(self):
        return get_project_root()
    
    def test_tooltip_helper_exists(self, project_root):
        """Ensure tooltip_helper module exists for theme-compatible tooltips"""
        filepath = project_root / 'UI' / 'tooltip_helper.py'
        assert filepath.exists(), \
            "UI/tooltip_helper.py should exist for theme-compatible tooltip handling"
        
        content = filepath.read_text(encoding='utf-8')
        
        # Should have InstantToolTipFilter class
        assert 'InstantToolTipFilter' in content, \
            "tooltip_helper should have InstantToolTipFilter class"
        assert 'install_tooltip' in content, \
            "tooltip_helper should have install_tooltip function"
    
    def test_pages_use_tooltip_helper(self, project_root):
        """Ensure pages with tooltips use tooltip_helper for theme compatibility"""
        pages_with_tooltips = [
            'UI/settings_page.py',
            'UI/probe/page.py',
        ]
        
        for page_path in pages_with_tooltips:
            filepath = project_root / page_path
            if not filepath.exists():
                continue
                
            content = filepath.read_text(encoding='utf-8')
            
            # If page has setToolTip, it should also use install_tooltip
            if 'setToolTip' in content:
                assert 'install_tooltip' in content or 'tooltip_helper' in content, \
                    f"{page_path} uses setToolTip but doesn't use tooltip_helper for theme compatibility"
