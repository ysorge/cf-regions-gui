"""Small native panel with a title-bar-style collapse control."""

from __future__ import annotations

from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class CollapsiblePanel(QFrame):
    """Keep a panel's title visible while its content is collapsed."""

    toggled = Signal(bool)

    def __init__(
        self,
        title: str,
        content: QWidget,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._content = content
        self._expanded = True
        self._last_expanded_height = 0
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._header = QWidget()
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(8, 4, 4, 4)
        title_label = QLabel(title)
        title_font = title_label.font()
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label, 1)

        self.toggle_button = QToolButton()
        self.toggle_button.setAutoRaise(True)
        self.toggle_button.clicked.connect(self.toggle)
        header_layout.addWidget(self.toggle_button)

        layout.addWidget(self._header)
        layout.addWidget(content)
        self._update_button()

    @property
    def is_expanded(self) -> bool:
        """Return whether the content is visible."""

        return self._expanded

    @property
    def last_expanded_height(self) -> int:
        """Return the panel height captured immediately before collapsing."""

        return self._last_expanded_height

    @property
    def collapsed_height(self) -> int:
        """Return the height retained while the content is collapsed."""

        return self._header.minimumSizeHint().height() + 2 * self.frameWidth()

    def minimumSizeHint(self) -> QSize:
        """Allow a splitter to shrink the panel as far as its title bar."""

        hint = super().minimumSizeHint()
        if not hasattr(self, "_header"):
            return hint
        return QSize(hint.width(), self.collapsed_height)

    def toggle(self) -> None:
        """Switch between the expanded and title-only states."""

        self.set_expanded(not self._expanded)

    def set_expanded(self, expanded: bool) -> None:
        """Set the content visibility while keeping the header accessible."""

        if self._expanded == expanded:
            return
        if not expanded:
            self._last_expanded_height = self.height()
        self._expanded = expanded
        self._content.setVisible(expanded)
        self._update_button()
        self.updateGeometry()
        self.toggled.emit(expanded)

    def _update_button(self) -> None:
        standard_icon = (
            QStyle.StandardPixmap.SP_TitleBarShadeButton
            if self._expanded
            else QStyle.StandardPixmap.SP_TitleBarUnshadeButton
        )
        action = "Collapse" if self._expanded else "Expand"
        self.toggle_button.setIcon(self.style().standardIcon(standard_icon))
        self.toggle_button.setToolTip(f"{action} selected region details")
        self.toggle_button.setAccessibleName(
            f"{action} selected region details"
        )
