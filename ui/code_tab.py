"""Pestaña Código: editor de .cns / .cmd / .st / .zss con colores, autocompletado, buscar y revisar."""
import re
from pathlib import Path

from PyQt6.QtCore import QRect, QRegularExpression, QSize, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor, QFont, QFontDatabase, QKeySequence, QPainter, QShortcut, QSyntaxHighlighter, QTextCharFormat,
    QTextCursor, QTextDocument, QTextFormat,
)
from PyQt6.QtWidgets import (
    QCheckBox, QCompleter, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPlainTextDocumentLayout, QPlainTextEdit, QPushButton, QSplitter, QTextEdit, QVBoxLayout, QWidget,
)

from core import codeinfo
from core.textio import read_text, write_text
from i18n import tr
from ui.common import APP_NAME, warn_banner


def fmt(color, bold=False, italic=False):
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Weight.Bold)
    if italic:
        f.setFontItalic(True)
    return f


class Highlighter(QSyntaxHighlighter):
    def __init__(self, doc, zss=False):
        super().__init__(doc)
        self.zss = zss
        words_s = "|".join(sorted(codeinfo.SCTRLS, key=len, reverse=True))
        words_t = "|".join(sorted(codeinfo.TRIGGERS, key=len, reverse=True))
        ci = QRegularExpression.PatternOption.CaseInsensitiveOption
        self.rules = [
            (QRegularExpression(r"\b(" + words_t + r")\b", ci), fmt("#7fc8ff"), 0),
            (QRegularExpression(r"\btype\s*[=:]\s*(" + words_s + r")\b", ci), fmt("#ffcb6b", True), 1),
            (QRegularExpression(r"\b(" + words_s + r")\s*(?=\{)", ci), fmt("#ffcb6b", True), 1),
            (QRegularExpression(r"^\s*[A-Za-z_][\w.]*\s*(?==)"), fmt("#c792ea"), 0),
            (QRegularExpression(r"\b-?\d+(\.\d+)?\b"), fmt("#f78c6c"), 0),
            (QRegularExpression(r"\b(parent|root|helper|target|partner|enemy|enemynear|playerid|var|fvar|sysvar|sysfvar|"
                                r"if|else|switch|case|default|let|for|while|break|continue|ignorehitpause|persistent)\b", ci),
             fmt("#89ddff"), 0),
            (QRegularExpression(r'"[^"]*"'), fmt("#c3e88d"), 0),
            (QRegularExpression(r"^\s*\[[^\]]*\]?"), fmt("#ffffff", True), 0),
        ]
        self.comment = fmt("#6a7a8c", italic=True)

    def highlightBlock(self, text):
        for rx, f, g in self.rules:
            it = rx.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(g), m.capturedLength(g), f)
        # comentarios al final (ganan a todo)
        q = False
        for i, ch in enumerate(text):
            if ch == '"':
                q = not q
            elif not q and ((ch == "#") if self.zss else (ch == ";")):
                self.setFormat(i, len(text) - i, self.comment)
                break


class LineNumbers(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.number_width(), 0)

    def paintEvent(self, e):
        self.editor.paint_numbers(e)


class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSize(max(10, font.pointSize()))
        self.setFont(font)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.numbers = LineNumbers(self)
        self.blockCountChanged.connect(lambda _n: self.setViewportMargins(self.number_width(), 0, 0, 0))
        self.updateRequest.connect(self.on_update_request)
        self.cursorPositionChanged.connect(self.highlight_line)
        self.setViewportMargins(self.number_width(), 0, 0, 0)
        self.setStyleSheet("QPlainTextEdit { background: #1e2228; color: #d6deeb; }")
        self.completer = QCompleter(codeinfo.WORDS, self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchStartsWith)
        self.completer.setWidget(self)
        self.completer.activated.connect(self.insert_completion)
        self.error_lines = set()

    # ---- números de línea
    def number_width(self):
        return 14 + self.fontMetrics().horizontalAdvance("9") * len(str(max(1, self.blockCount())))

    def on_update_request(self, rect, dy):
        if dy:
            self.numbers.scroll(0, dy)
        else:
            self.numbers.update(0, rect.y(), self.numbers.width(), rect.height())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        cr = self.contentsRect()
        self.numbers.setGeometry(QRect(cr.left(), cr.top(), self.number_width(), cr.height()))

    def paint_numbers(self, e):
        p = QPainter(self.numbers)
        p.fillRect(e.rect(), QColor("#16191e"))
        block = self.firstVisibleBlock()
        n = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        while block.isValid() and top <= e.rect().bottom():
            if block.isVisible() and bottom >= e.rect().top():
                p.setPen(QColor("#ff6b6b") if (n + 1) in self.error_lines else QColor("#5c6773"))
                p.drawText(0, top, self.numbers.width() - 6, self.fontMetrics().height(),
                           Qt.AlignmentFlag.AlignRight, str(n + 1))
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            n += 1

    def highlight_line(self):
        sel = QTextEdit.ExtraSelection()
        sel.format.setBackground(QColor("#262b33"))
        sel.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        sel.cursor = self.textCursor()
        sel.cursor.clearSelection()
        self.setExtraSelections([sel])

    def go_line(self, n):
        block = self.document().findBlockByNumber(max(0, n - 1))
        c = QTextCursor(block)
        self.setTextCursor(c)
        self.centerCursor()
        self.setFocus()

    # ---- ayuda al pasar el ratón
    def event(self, e):
        from PyQt6.QtCore import QEvent
        if e.type() == QEvent.Type.ToolTip:
            from PyQt6.QtWidgets import QToolTip
            from core.docs import doc_for
            pos = e.pos() - self.viewport().pos()
            c = self.cursorForPosition(pos)
            text = c.block().text()
            i = c.positionInBlock()
            a = i
            while a > 0 and (text[a - 1].isalnum() or text[a - 1] in "_."):
                a -= 1
            b = i
            while b < len(text) and (text[b].isalnum() or text[b] in "_."):
                b += 1
            word = text[a:b]
            doc = doc_for(word) if word else None
            if doc:
                QToolTip.showText(e.globalPos(), doc, self)
            else:
                QToolTip.hideText()
            return True
        return super().event(e)

    # ---- autocompletar
    def word_under(self):
        c = self.textCursor()
        text = c.block().text()[:c.positionInBlock()]
        m = re.search(r"[A-Za-z_][\w.]*$", text)
        return m.group(0) if m else ""

    def insert_completion(self, word):
        c = self.textCursor()
        prefix = self.word_under()
        c.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, len(prefix))
        c.insertText(word)
        self.setTextCursor(c)

    def keyPressEvent(self, e):
        popup = self.completer.popup()
        if popup.isVisible() and e.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Tab,
                                             Qt.Key.Key_Escape, Qt.Key.Key_Backtab):
            e.ignore()
            return
        force = e.key() == Qt.Key.Key_Space and e.modifiers() & Qt.KeyboardModifier.ControlModifier
        if not force:
            if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                # mantener la sangría
                indent = re.match(r"^\s*", self.textCursor().block().text()).group(0)
                super().keyPressEvent(e)
                self.insertPlainText(indent)
                return
            super().keyPressEvent(e)
        prefix = self.word_under()
        if not force and (len(prefix) < 3 or not e.text() or not (e.text().isalnum() or e.text() in "_.")):
            popup.hide()
            return
        self.completer.setCompletionPrefix(prefix)
        if self.completer.completionCount() == 0 or (
                self.completer.completionCount() == 1 and self.completer.currentCompletion().lower() == prefix.lower()):
            popup.hide()
            return
        popup.setCurrentIndex(self.completer.completionModel().index(0, 0))
        r = self.cursorRect()
        r.setWidth(popup.sizeHintForColumn(0) + popup.verticalScrollBar().sizeHint().width() + 20)
        self.completer.complete(r)


class OpenFile:
    def __init__(self, path):
        self.path = Path(path)
        text, self.enc, self.nl = read_text(path)
        self.doc = QTextDocument()
        self.doc.setDocumentLayout(QPlainTextDocumentLayout(self.doc))
        self.doc.setPlainText(text)
        self.doc.setModified(False)
        self.kind = "zss" if self.path.suffix.lower() == ".zss" else ("cmd" if self.path.suffix.lower() == ".cmd" else "cns")
        self.hl = Highlighter(self.doc, self.kind == "zss")


class CodeTab(QWidget):
    modifiedChanged = pyqtSignal()

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.open = {}
        self.cur = None
        lay = QHBoxLayout(self)
        split = QSplitter()
        lay.addWidget(split)
        left = QSplitter(Qt.Orientation.Vertical)
        self.files = QListWidget()
        self.files.currentItemChanged.connect(self.on_file)
        left.addWidget(self.files)
        ow = QWidget()
        ol = QVBoxLayout(ow)
        ol.setContentsMargins(0, 0, 0, 0)
        self.outline_filter = QLineEdit()
        self.outline_filter.setPlaceholderText(tr('Ir a estado / comando…'))
        self.outline_filter.textChanged.connect(lambda _t: self.fill_outline())
        ol.addWidget(self.outline_filter)
        self.outline = QListWidget()
        self.outline.itemClicked.connect(lambda it: self.editor.go_line(it.data(Qt.ItemDataRole.UserRole)))
        ol.addWidget(self.outline, 1)
        left.addWidget(ow)
        left.setSizes([220, 480])
        split.addWidget(left)
        right = QSplitter(Qt.Orientation.Vertical)
        ew = QWidget()
        el = QVBoxLayout(ew)
        el.setContentsMargins(0, 0, 0, 0)
        self.editor = CodeEditor()
        self.editor.setEnabled(False)
        self.gen_banner = warn_banner()
        el.addWidget(self.gen_banner)
        el.addWidget(self.editor, 1)
        self.warned = set()
        # buscar / reemplazar
        self.find_bar = QWidget()
        fb = QHBoxLayout(self.find_bar)
        fb.setContentsMargins(0, 0, 0, 0)
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText(tr('Buscar'))
        self.find_edit.returnPressed.connect(lambda: self.find(True))
        self.repl_edit = QLineEdit()
        self.repl_edit.setPlaceholderText(tr('Reemplazar con'))
        self.case = QCheckBox(tr('Mayúsculas'))
        fb.addWidget(self.find_edit, 2)
        for txt, fn in ((tr('⬆'), lambda: self.find(False)), (tr('⬇'), lambda: self.find(True))):
            b = QPushButton(txt)
            b.setFixedWidth(34)
            b.clicked.connect(fn)
            fb.addWidget(b)
        fb.addWidget(self.repl_edit, 2)
        for txt, fn in ((tr('Reemplazar'), self.replace_one), (tr('Todos'), self.replace_all)):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            fb.addWidget(b)
        fb.addWidget(self.case)
        el.addWidget(self.find_bar)
        bar = QHBoxLayout()
        self.pos_lbl = QLabel()
        self.editor.cursorPositionChanged.connect(self.update_pos)
        bar.addWidget(self.pos_lbl)
        bar.addStretch(1)
        chk = QPushButton(tr('🔍 Revisar errores'))
        chk.setShortcut(QKeySequence("F7"))
        chk.clicked.connect(self.run_check)
        bar.addWidget(chk)
        el.addLayout(bar)
        right.addWidget(ew)
        self.problems = QListWidget()
        self.problems.itemClicked.connect(lambda it: self.editor.go_line(it.data(Qt.ItemDataRole.UserRole)))
        right.addWidget(self.problems)
        right.setSizes([700, 120])
        split.addWidget(right)
        split.setSizes([260, 1100])
        for key, fn in (("Ctrl+F", lambda: (self.find_edit.setFocus(), self.find_edit.selectAll())),
                        ("F3", lambda: self.find(True)), ("Shift+F3", lambda: self.find(False)),
                        ("Ctrl+G", self.goto_line)):
            sc = QShortcut(QKeySequence(key), self)
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(fn)

    # ---- lo que arma el modo simple (se rehace solo: lo editado a mano ahí se pierde)
    @staticmethod
    def gen_regions(of):
        """Partes del archivo que rehace el modo simple: [(desde, hasta)] en caracteres."""
        from core import simple_gen as sg
        text = of.doc.toPlainText()
        if of.path.name.lower().endswith("_simple.st"):
            return [(0, len(text) + 1)]
        out = []
        for a, b in ((sg.CMD_BEGIN, sg.CMD_END), (sg.ENT_BEGIN, sg.ENT_END)):
            i = text.find(a)
            j = text.find(b, i + 1) if i >= 0 else -1
            if i >= 0 and j >= 0:
                out.append((i, j + len(b)))
        return out

    def show_gen_banner(self):
        of = self.cur
        regions = self.gen_regions(of) if of else []
        if not regions:
            self.gen_banner.hide()
            return
        if of.path.name.lower().endswith("_simple.st"):
            msg = tr('⚠ <b>Este archivo lo hace el modo simple.</b> Se vuelve a armar completo cada vez que cambias '
                     'algo en el modo simple, así que lo que edites aquí se pierde. Para código tuyo usa otro '
                     'archivo (o un evento «Código propio» del especial).')
        else:
            msg = tr('⚠ Lo que está entre las marcas <b>«SIMPLE-MODE»</b> lo hace el modo simple y se vuelve a '
                     'armar cada vez que cambias algo allá: lo que edites ahí adentro se pierde. Lo demás del '
                     'archivo es tuyo.')
        self.gen_banner.setText(msg)
        self.gen_banner.show()

    def on_contents(self, of, pos, _removed, _added):
        # solo lo que escribe la persona (el modo simple también cambia estos documentos, pero sin el cursor aquí)
        if str(of.path) in self.warned or of is not self.cur or not self.editor.hasFocus():
            return
        if not any(a <= pos <= b for a, b in self.gen_regions(of)):
            return
        self.warned.add(str(of.path))
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: QMessageBox.warning(self, APP_NAME, tr(
            'Ojo: esto lo hace el modo simple. La próxima vez que cambies algo en el modo simple se vuelve a armar '
            'y lo que escribiste aquí se pierde.\n\nSi quieres que se quede, ponlo fuera de las marcas '
            '«SIMPLE-MODE» o en otro archivo.')))

    def track(self, item, of):
        of.doc.modificationChanged.connect(lambda _m, it=item, of=of: self.on_modified(it, of))
        of.doc.contentsChange.connect(lambda pos, r, a, of=of: self.on_contents(of, pos, r, a))

    def load(self):
        self.open = {}
        self.cur = None
        self.warned = set()
        self.files.clear()
        self.problems.clear()
        p = self.main.project
        if not p:
            return
        for key, path in p.code_files():
            if path.resolve() == p.def_path.resolve():
                continue  # el .def se edita en «Datos»
            rel = path.relative_to(p.folder).as_posix() if path.is_relative_to(p.folder) else str(path)
            it = QListWidgetItem(f"{rel}" + (f"   ({key})" if key else ""))
            it.setData(Qt.ItemDataRole.UserRole, str(path))
            self.files.addItem(it)
        self.editor.setEnabled(self.files.count() > 0)
        if self.files.count():
            self.files.setCurrentRow(0)

    def on_file(self, item, _prev=None):
        if not item:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        if path not in self.open:
            try:
                of = OpenFile(path)
            except OSError as e:
                QMessageBox.warning(self, APP_NAME, str(e))
                return
            self.track(item, of)
            self.open[path] = of
        self.cur = self.open[path]
        self.show_gen_banner()
        self.editor.setDocument(self.cur.doc)
        self.editor.setViewportMargins(self.editor.number_width(), 0, 0, 0)
        self.editor.error_lines = set()
        self.fill_outline()
        self.problems.clear()

    def get_open(self, path):
        """El archivo abierto (lo abre si hace falta), para que otras partes le agreguen código."""
        path = str(Path(path))
        item = None
        for i in range(self.files.count()):
            if self.files.item(i).data(Qt.ItemDataRole.UserRole) == path:
                item = self.files.item(i)
                break
        if item is None:
            p = self.main.project
            rel = Path(path).relative_to(p.folder).as_posix() if Path(path).is_relative_to(p.folder) else path
            item = QListWidgetItem(rel)
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.files.addItem(item)
            self.editor.setEnabled(True)
        if path not in self.open:
            of = OpenFile(path)
            self.track(item, of)
            self.open[path] = of
        return self.open[path]

    def on_modified(self, item, of):
        name = item.text().lstrip("● ")
        item.setText(("● " if of.doc.isModified() else "") + name)
        self.modifiedChanged.emit()

    def fill_outline(self):
        self.outline.clear()
        if not self.cur:
            return
        flt = self.outline_filter.text().strip().lower()
        for n, text in codeinfo.outline(self.cur.doc.toPlainText(), self.cur.kind):
            if flt and flt not in text.lower():
                continue
            it = QListWidgetItem(text)
            it.setData(Qt.ItemDataRole.UserRole, n)
            self.outline.addItem(it)

    def update_pos(self):
        c = self.editor.textCursor()
        self.pos_lbl.setText(tr('Línea {0}, columna {1}').format(c.blockNumber() + 1, c.positionInBlock() + 1))

    # ---- buscar
    def find(self, forward=True):
        text = self.find_edit.text()
        if not text or not self.cur:
            return False
        flags = QTextDocument.FindFlag(0)
        if not forward:
            flags |= QTextDocument.FindFlag.FindBackward
        if self.case.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if not self.editor.find(text, flags):
            c = self.editor.textCursor()
            c.movePosition(QTextCursor.MoveOperation.Start if forward else QTextCursor.MoveOperation.End)
            self.editor.setTextCursor(c)
            return self.editor.find(text, flags)
        return True

    def replace_one(self):
        c = self.editor.textCursor()
        if c.hasSelection() and c.selectedText().lower() == self.find_edit.text().lower():
            c.insertText(self.repl_edit.text())
        self.find(True)

    def replace_all(self):
        if not self.cur or not self.find_edit.text():
            return
        text = self.cur.doc.toPlainText()
        pat = re.escape(self.find_edit.text())
        new, n = re.subn(pat, lambda _m: self.repl_edit.text(), text, flags=0 if self.case.isChecked() else re.IGNORECASE)
        if n:
            c = QTextCursor(self.cur.doc)
            c.select(QTextCursor.SelectionType.Document)
            c.insertText(new)
        self.main.status.setText(tr('{0} reemplazo(s)').format(n))

    def goto_line(self):
        from PyQt6.QtWidgets import QInputDialog
        n, ok = QInputDialog.getInt(self, tr('Ir a la línea'), tr('Línea:'), 1, 1, max(1, self.editor.blockCount()))
        if ok:
            self.editor.go_line(n)

    # ---- revisar
    def run_check(self):
        if not self.cur:
            return
        p = self.main.project
        states = set()
        for _k, path in p.code_files():
            if path.suffix.lower() in (".cns", ".st", ".zss"):
                of = self.open.get(str(path))
                try:
                    text = of.doc.toPlainText() if of else read_text(path)[0]
                except OSError:
                    continue
                states |= codeinfo.statedefs_in(text)
        anims = {a.number for a in p.air.actions} if p.file("anim") or p.air_loaded() else None
        sounds = {s.key for s in p.snd.sounds} if p.file("sound") or p.snd_loaded() else None
        issues = codeinfo.check(self.cur.doc.toPlainText(), self.cur.kind, states, anims, sounds)
        self.problems.clear()
        self.editor.error_lines = {n for n, lvl, _m in issues if lvl == "error"}
        self.editor.numbers.update()
        if not issues:
            it = QListWidgetItem(tr('✅ No encontré problemas.'))
            self.problems.addItem(it)
            return
        for n, lvl, msg in issues:
            it = QListWidgetItem(("❌ " if lvl == "error" else "⚠ ") + tr('Línea {0}: {1}').format(n, msg))
            it.setData(Qt.ItemDataRole.UserRole, n)
            self.problems.addItem(it)

    # ---- guardar
    def is_modified(self):
        return any(of.doc.isModified() for of in self.open.values())

    def save(self):
        ok = True
        for of in self.open.values():
            if of.doc.isModified():
                try:
                    self.main.project.backup(of.path)
                    write_text(of.path, of.doc.toPlainText(), of.enc, of.nl)
                    of.doc.setModified(False)
                except OSError as e:
                    QMessageBox.warning(self, APP_NAME, tr('No pude guardar {0}: {1}').format(of.path.name, e))
                    ok = False
        return ok
