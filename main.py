import sys
import os
import json
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QTableView, QMessageBox, QStatusBar

DATASET_PATH_DEFAULT = r"academic_english_dataset.json"

class DatasetModel(QAbstractTableModel):
    def __init__(self, rows=None):
        super().__init__()
        self.columns = [
            "word",
            "phonetic",
            "partOfSpeech",
            "definition",
            "chineseTranslation",
            "frequency",
            "field",
            "exampleSentence",
            "notesEnglish",
            "notesChinese",
        ]
        self.rows = rows or []
        self.lang = "zh"

    def rowCount(self, parent=QModelIndex()):
        return len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return len(self.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            row = self.rows[index.row()]
            key = self.columns[index.column()]
            val = row.get(key, "")
            return val
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            headers_zh = {
                "word": "词",
                "phonetic": "音标",
                "partOfSpeech": "词性",
                "definition": "英文释义",
                "chineseTranslation": "中文翻译",
                "frequency": "频率",
                "field": "领域",
                "exampleSentence": "例句",
                "notesEnglish": "Note（English）",
                "notesChinese": "Note（中文）",
            }
            headers_en = {
                "word": "Word",
                "phonetic": "Phonetic",
                "partOfSpeech": "Part of Speech",
                "definition": "Definition",
                "chineseTranslation": "Chinese Translation",
                "frequency": "Frequency",
                "field": "Field",
                "exampleSentence": "Example",
                "notesEnglish": "Note (English)",
                "notesChinese": "Note (Chinese)",
            }
            headers = headers_zh if self.lang == "zh" else headers_en
            return headers.get(self.columns[section], self.columns[section])
        return section + 1

    def flags(self, index):
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def setLanguage(self, lang):
        self.lang = lang
        self.headerDataChanged.emit(Qt.Horizontal, 0, self.columnCount()-1)

class VocabularyFilterProxy(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.search_text = ""
        self.frequency_filter = "ALL"
        self.field_filter = "ALL"
        self.pos_filter = "ALL"
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setSortCaseSensitivity(Qt.CaseInsensitive)

    def setSearchText(self, text):
        self.search_text = text.strip()
        self.invalidateFilter()

    def setFrequency(self, freq):
        self.frequency_filter = "ALL" if freq in ("全部", "All") else freq
        self.invalidateFilter()

    def setField(self, field):
        self.field_filter = "ALL" if field in ("全部", "All") else field
        self.invalidateFilter()

    def setPOS(self, pos):
        self.pos_filter = "ALL" if pos in ("全部", "All") else pos
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        if model is None:
            return True
        def get(col):
            idx = model.index(source_row, model.columns.index(col))
            v = model.data(idx, Qt.DisplayRole)
            return v if isinstance(v, str) else str(v)
        word = get("word")
        phonetic = get("phonetic")
        pos = get("partOfSpeech")
        definition = get("definition")
        zh = get("chineseTranslation")
        freq = get("frequency")
        field = get("field")
        example = get("exampleSentence")
        notes_en = get("notesEnglish")
        notes_zh = get("notesChinese")
        if self.frequency_filter != "ALL" and freq != self.frequency_filter:
            return False
        if self.pos_filter != "ALL" and pos != self.pos_filter:
            return False
        if self.field_filter != "ALL":
            tokens = [t.strip() for t in field.split(",")]
            if self.field_filter not in tokens:
                return False
        if self.search_text:
            s = self.search_text.lower()
            blob = " \n ".join([word, phonetic, pos, definition, zh, freq, field, example, notes_en, notes_zh]).lower()
            if s not in blob:
                return False
        return True

class MainWindow(QMainWindow):
    def __init__(self, dataset_path):
        super().__init__()
        self.lang = "zh"
        self.setWindowTitle("学术英语词汇库")
        self.resize(1200, 700)
        self.dataset_path = dataset_path
        self.model = DatasetModel([])
        self.proxy = VocabularyFilterProxy()
        self.proxy.setSourceModel(self.model)

        cw = QWidget()
        self.setCentralWidget(cw)
        layout = QVBoxLayout(cw)

        filters = QHBoxLayout()
        layout.addLayout(filters)

        self.lbl_search = QLabel("搜索:")
        filters.addWidget(self.lbl_search)
        self.search = QLineEdit()
        self.search.setPlaceholderText("按词、定义、中文、领域等搜索")
        filters.addWidget(self.search)

        self.lbl_freq = QLabel("频率:")
        filters.addWidget(self.lbl_freq)
        self.freq = QComboBox()
        self.freq.addItem("全部")
        filters.addWidget(self.freq)

        self.lbl_field = QLabel("领域:")
        filters.addWidget(self.lbl_field)
        self.field = QComboBox()
        self.field.addItem("全部")
        filters.addWidget(self.field)

        self.lbl_pos = QLabel("词性:")
        filters.addWidget(self.lbl_pos)
        self.pos = QComboBox()
        self.pos.addItem("全部")
        filters.addWidget(self.pos)

        self.clear_btn = QPushButton("清空筛选")
        filters.addWidget(self.clear_btn)
        self.reload_btn = QPushButton("重新加载")
        filters.addWidget(self.reload_btn)
        self.toggle_lang_btn = QPushButton("切换为英文")
        filters.addWidget(self.toggle_lang_btn)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        status = QStatusBar()
        self.setStatusBar(status)
        self.status_total = QLabel()
        self.status_filtered = QLabel()
        status.addPermanentWidget(self.status_total)
        status.addPermanentWidget(self.status_filtered)

        self.search.textChanged.connect(self.proxy.setSearchText)
        self.freq.currentTextChanged.connect(self.proxy.setFrequency)
        self.field.currentTextChanged.connect(self.proxy.setField)
        self.pos.currentTextChanged.connect(self.proxy.setPOS)
        self.clear_btn.clicked.connect(self.clearFilters)
        self.reload_btn.clicked.connect(self.loadDataset)
        self.toggle_lang_btn.clicked.connect(self.toggleLanguage)
        self.proxy.rowsInserted.connect(self.updateStatus)
        self.proxy.rowsRemoved.connect(self.updateStatus)
        self.proxy.modelReset.connect(self.updateStatus)
        self.proxy.rowsInserted.connect(self.resizeColumns)
        self.proxy.modelReset.connect(self.resizeColumns)

        self.loadDataset()
        self.applyLanguage()

    def clearFilters(self):
        self.search.clear()
        self.freq.setCurrentIndex(0)
        self.field.setCurrentIndex(0)
        self.pos.setCurrentIndex(0)

    def loadDataset(self):
        path = self.dataset_path
        if not os.path.exists(path):
            local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "academic_english_dataset.json")
            path = local if os.path.exists(local) else path
        try:
            with open(path, "r", encoding="utf-8") as f:
                base_rows = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法读取数据文件: {e}")
            return
        rows = []
        for r in base_rows:
            notes = r.get("notes", "")
            en, zh = self.splitNotes(notes)
            rr = dict(r)
            rr["notesEnglish"] = en
            rr["notesChinese"] = zh
            rows.append(rr)
        self.model.beginResetModel()
        self.model.rows = rows
        self.model.endResetModel()
        self.populateFilters(rows)
        self.updateStatus()

    def populateFilters(self, rows):
        freq_head = "全部" if self.lang == "zh" else "All"
        freq_set = [freq_head] + sorted({r.get("frequency", "") for r in rows if r.get("frequency")})
        field_tokens = set()
        for r in rows:
            s = r.get("field", "")
            for t in s.split(","):
                t = t.strip()
                if t:
                    field_tokens.add(t)
        field_set = [freq_head] + sorted(field_tokens)
        pos_set = [freq_head] + sorted({r.get("partOfSpeech", "") for r in rows if r.get("partOfSpeech")})
        self.freq.blockSignals(True)
        self.field.blockSignals(True)
        self.pos.blockSignals(True)
        self.freq.clear()
        self.field.clear()
        self.pos.clear()
        self.freq.addItems(freq_set)
        self.field.addItems(field_set)
        self.pos.addItems(pos_set)
        self.freq.blockSignals(False)
        self.field.blockSignals(False)
        self.pos.blockSignals(False)

    def updateStatus(self):
        total = self.model.rowCount()
        filtered = self.proxy.rowCount()
        if self.lang == "zh":
            self.status_total.setText(f"总计: {total}")
            self.status_filtered.setText(f"已筛选: {filtered}")
        else:
            self.status_total.setText(f"Total: {total}")
            self.status_filtered.setText(f"Filtered: {filtered}")

    def resizeColumns(self):
        for i in range(self.model.columnCount()):
            self.table.resizeColumnToContents(i)
        try:
            idx_pos = self.model.columns.index("partOfSpeech")
            idx_freq = self.model.columns.index("frequency")
            self.table.setColumnWidth(idx_pos, max(self.table.columnWidth(idx_pos), 180))
            self.table.setColumnWidth(idx_freq, max(self.table.columnWidth(idx_freq), 120))
        except ValueError:
            pass

    def splitNotes(self, text):
        if not isinstance(text, str):
            return "", ""
        s = text.strip()
        if not s:
            return "", ""
        import re
        en = ""
        zh = ""
        m_en = re.search(r"English\s*:\s*(.*?)(?:\s*Chinese\s*:\s*|$)", s, flags=re.S|re.I)
        m_zh = re.search(r"Chinese\s*:\s*(.*)$", s, flags=re.S|re.I)
        if m_en:
            en = m_en.group(1).strip()
        if m_zh:
            zh = m_zh.group(1).strip()
        if not en and not zh:
            m_en = re.search(r"英文\s*:\s*(.*?)(?:\s*中文\s*:\s*|$)", s, flags=re.S)
            m_zh = re.search(r"中文\s*:\s*(.*)$", s, flags=re.S)
            if m_en:
                en = m_en.group(1).strip()
            if m_zh:
                zh = m_zh.group(1).strip()
        return en, zh

    def toggleLanguage(self):
        self.lang = "en" if self.lang == "zh" else "zh"
        self.applyLanguage()
        self.model.setLanguage(self.lang)
        self.populateFilters(self.model.rows)
        self.updateStatus()

    def applyLanguage(self):
        if self.lang == "zh":
            self.setWindowTitle("学术英语词汇库")
            self.lbl_search.setText("搜索:")
            self.search.setPlaceholderText("按词、定义、中文、领域等搜索")
            self.lbl_freq.setText("频率:")
            self.lbl_field.setText("领域:")
            self.lbl_pos.setText("词性:")
            self.clear_btn.setText("清空筛选")
            self.reload_btn.setText("重新加载")
            self.toggle_lang_btn.setText("切换为英文")
        else:
            self.setWindowTitle("Academic English Vocabulary")
            self.lbl_search.setText("Search:")
            self.search.setPlaceholderText("Search by word, definition, Chinese, field, etc.")
            self.lbl_freq.setText("Frequency:")
            self.lbl_field.setText("Field:")
            self.lbl_pos.setText("Part of Speech:")
            self.clear_btn.setText("Clear Filters")
            self.reload_btn.setText("Reload")
            self.toggle_lang_btn.setText("Switch to Chinese")

def main():
    app = QApplication(sys.argv)
    window = MainWindow(DATASET_PATH_DEFAULT)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
