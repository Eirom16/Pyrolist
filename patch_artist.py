import sys

def patch():
    with open('src/pyrolist/ui/screens/artist.py', 'r') as f:
        content = f.read()
        
    old_build = """    def _build_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.content_widget = QWidget()
        self._content_wrapper_layout = QVBoxLayout(self.content_widget)
        self._content_wrapper_layout.setContentsMargins(0, 0, 0, 0)

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(24, 24, 24, 112)
        self.content_layout.setSpacing(16)

        self._content_wrapper_layout.addLayout(self.content_layout)
        self._content_wrapper_layout.addStretch()

        self.scroll.setWidget(self.content_widget)
        self.layout.addWidget(self.scroll)"""

    new_build = """    def _build_ui(self):
        from PySide6.QtWidgets import QStackedLayout, QGraphicsBlurEffect
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.stack = QStackedLayout()
        self.stack.setStackingMode(QStackedLayout.StackingMode.StackAll)
        self.layout.addLayout(self.stack)

        # 1. Blurred Background Image
        self.bg_image = QLabel()
        self.bg_image.setScaledContents(True)
        self.bg_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(80)
        self.bg_image.setGraphicsEffect(blur)
        
        # 2. Gradient Overlay
        self.bg_overlay = QWidget()
        self.bg_overlay.setStyleSheet(f\"\"\"
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(0,0,0,120),
                stop:0.4 {tokens.CURRENT.bg_base},
                stop:1 {tokens.CURRENT.bg_base});
        \"\"\")

        # Combine BG
        bg_container = QWidget()
        bg_layout = QVBoxLayout(bg_container)
        bg_layout.setContentsMargins(0,0,0,0)
        bg_layout.addWidget(self.bg_image)
        
        overlay_layout = QVBoxLayout(self.bg_overlay)
        overlay_layout.setContentsMargins(0,0,0,0)
        
        self.stack.addWidget(bg_container)
        self.stack.addWidget(self.bg_overlay)

        # 3. Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self._content_wrapper_layout = QVBoxLayout(self.content_widget)
        self._content_wrapper_layout.setContentsMargins(0, 0, 0, 0)

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(40, 40, 40, 112)
        self.content_layout.setSpacing(24)

        self._content_wrapper_layout.addLayout(self.content_layout)
        self._content_wrapper_layout.addStretch()

        self.scroll.setWidget(self.content_widget)
        self.stack.addWidget(self.scroll)"""

    content = content.replace(old_build, new_build)

    old_display = """    async def _display_artist(self, data: dict):
        self._clear_content()

        if not data:
            err = QLabel("Artista no encontrado")
            err.setStyleSheet(f"color: {tokens.CURRENT.text_secondary}; background: transparent;")
            self.content_layout.addWidget(err)
            return

        name = data.get('name', 'Unknown')
        subscribers = data.get('subscribers', '')
        thumbnail_url = ""
        thumbnails = data.get('thumbnails', [])
        if thumbnails:
            thumbnail_url = thumbnails[-1].get('url', '')

        # ── Back button ─────────────────────────────────────────────────
        back_row = QHBoxLayout()
        back_row.setContentsMargins(0, 0, 0, 8)
        btn_back = QPushButton()
        btn_back.setIcon(Icon.icon("arrow_back", tokens.CURRENT.text_secondary, 16))
        btn_back.setText("Volver")
        btn_back.setFont(AppFont.label(12))
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.setStyleSheet(f\"\"\"
            QPushButton {{
                background: transparent;
                border: none;
                padding: 6px 12px;
                border-radius: 8px;
                color: {tokens.CURRENT.text_secondary};
            }}
            QPushButton:hover {{
                background: {tokens.CURRENT.bg_elevated};
                color: {tokens.CURRENT.text_primary};
            }}
        \"\"\")
        btn_back.setFixedHeight(36)
        if self.on_back:
            btn_back.clicked.connect(self.on_back)
        back_row.addWidget(btn_back)
        back_row.addStretch()
        self.content_layout.addLayout(back_row)

        # ── Hero header ─────────────────────────────────────────────────
        header_layout = QHBoxLayout()
        header_layout.setSpacing(28)

        self.cover = QLabel()
        self.cover.setFixedSize(200, 200)
        self.cover.setObjectName("artistCover")
        cover_shadow = QGraphicsDropShadowEffect(self.cover)
        cover_shadow.setBlurRadius(24)
        cover_shadow.setOffset(0, 6)
        cover_shadow.setColor(QColor(0, 0, 0, 80))
        self.cover.setGraphicsEffect(cover_shadow)
        header_layout.addWidget(self.cover)

        if thumbnail_url:
            asyncio.ensure_future(self._load_cover(thumbnail_url))

        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)

        type_lbl = QLabel("ARTISTA")
        type_lbl.setFont(AppFont.label(11))
        type_lbl.setStyleSheet(f"color: {tokens.CURRENT.accent}; background: transparent; letter-spacing: 1px;")
        type_lbl.setObjectName("artistType")
        info_layout.addWidget(type_lbl)

        title_lbl = QLabel(name)
        title_lbl.setFont(AppFont.display(32))
        title_lbl.setStyleSheet(f"color: {tokens.CURRENT.text_primary}; background: transparent;")
        title_lbl.setObjectName("artistTitle")
        title_lbl.setWordWrap(True)
        info_layout.addWidget(title_lbl)

        if subscribers:
            meta_lbl = QLabel(subscribers)
            meta_lbl.setFont(AppFont.body(13))
            meta_lbl.setStyleSheet(f"color: {tokens.CURRENT.text_secondary}; background: transparent;")
            meta_lbl.setObjectName("artistMeta")
            info_layout.addWidget(meta_lbl)

        # ── Action buttons ────────────────────────────────────────────
        actions_row = QHBoxLayout()
        actions_row.setSpacing(12)
        actions_row.setContentsMargins(0, 8, 0, 0)

        play_all_btn = QPushButton()
        play_all_btn.setIcon(Icon.icon("play_arrow", tokens.CURRENT.text_on_accent, 20))
        play_all_btn.setText("Reproducir")
        play_all_btn.setFont(AppFont.title(13))
        play_all_btn.setFixedHeight(44)
        play_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        play_all_btn.setStyleSheet(f\"\"\"
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {tokens.CURRENT.accent},
                    stop:1 {tokens.CURRENT.accent_bright});
                color: {tokens.CURRENT.text_on_accent};
                border: none;
                border-radius: 22px;
                padding: 0 24px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {tokens.CURRENT.accent_bright},
                    stop:1 {tokens.CURRENT.accent});
            }}
        \"\"\")
        play_all_btn.clicked.connect(lambda: self._play_first_song(data))
        actions_row.addWidget(play_all_btn)

        shuffle_btn = QPushButton()
        shuffle_btn.setIcon(Icon.icon("shuffle", tokens.CURRENT.text_primary, 18))
        shuffle_btn.setText("Aleatorio")
        shuffle_btn.setFont(AppFont.title(13))
        shuffle_btn.setFixedHeight(44)
        shuffle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        shuffle_btn.setStyleSheet(f\"\"\"
            QPushButton {{
                background: {tokens.CURRENT.bg_elevated};
                color: {tokens.CURRENT.text_primary};
                border: 1px solid {tokens.CURRENT.border};
                border-radius: 22px;
                padding: 0 24px;
            }}
            QPushButton:hover {{
                background: {tokens.CURRENT.bg_high};
                border-color: {tokens.CURRENT.accent};
            }}
        \"\"\")
        songs = data.get('songs', {}).get('results', [])
        if songs:
            import random
            shuffle_btn.clicked.connect(lambda: self._play_song(
                random.choice(songs), data.get('name', 'Unknown')
            ))
        actions_row.addWidget(shuffle_btn)
        actions_row.addStretch()
        info_layout.addLayout(actions_row)

        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        self.content_layout.addLayout(header_layout)"""

    new_display = """    async def _display_artist(self, data: dict):
        self._clear_content()

        if not data:
            err = QLabel("Artista no encontrado")
            err.setStyleSheet(f"color: {tokens.CURRENT.text_secondary}; background: transparent;")
            self.content_layout.addWidget(err)
            return

        name = data.get('name', 'Unknown')
        subscribers = data.get('subscribers', '')
        thumbnail_url = ""
        thumbnails = data.get('thumbnails', [])
        if thumbnails:
            thumbnail_url = thumbnails[-1].get('url', '')

        # ── Back button ─────────────────────────────────────────────────
        back_row = QHBoxLayout()
        back_row.setContentsMargins(0, 0, 0, 8)
        btn_back = QPushButton()
        btn_back.setIcon(Icon.icon("arrow_back", tokens.CURRENT.text_secondary, 16))
        btn_back.setText("Volver")
        btn_back.setFont(AppFont.label(12))
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.setStyleSheet(f\"\"\"
            QPushButton {{
                background: transparent;
                border: none;
                padding: 6px 12px;
                border-radius: 8px;
                color: {tokens.CURRENT.text_secondary};
            }}
            QPushButton:hover {{
                background: {tokens.CURRENT.bg_elevated};
                color: {tokens.CURRENT.text_primary};
            }}
        \"\"\")
        btn_back.setFixedHeight(36)
        if self.on_back:
            btn_back.clicked.connect(self.on_back)
        back_row.addWidget(btn_back)
        back_row.addStretch()
        self.content_layout.addLayout(back_row)

        # ── Immersive Hero Header ──────────────────────────────────────────
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 40, 0, 20)
        header_layout.setSpacing(20)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Circular Cover Image
        self.cover = QLabel()
        self.cover.setFixedSize(200, 200)
        self.cover.setObjectName("artistCover")
        self.cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Premium Shadow
        cover_shadow = QGraphicsDropShadowEffect(self.cover)
        cover_shadow.setBlurRadius(40)
        cover_shadow.setOffset(0, 10)
        cover_shadow.setColor(QColor(0, 0, 0, 140))
        self.cover.setGraphicsEffect(cover_shadow)
        
        header_layout.addWidget(self.cover, alignment=Qt.AlignmentFlag.AlignCenter)

        if thumbnail_url:
            asyncio.ensure_future(self._load_cover(thumbnail_url))

        # Artist Info (Centered)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_lbl = QLabel(name)
        title_lbl.setFont(AppFont.display(48))
        title_lbl.setStyleSheet(f"color: {tokens.CURRENT.text_primary}; background: transparent; font-weight: bold;")
        title_lbl.setObjectName("artistTitle")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setWordWrap(True)
        info_layout.addWidget(title_lbl)

        if subscribers:
            meta_lbl = QLabel(f"{subscribers} • Artista")
            meta_lbl.setFont(AppFont.body(14))
            meta_lbl.setStyleSheet(f"color: rgba(255, 255, 255, 0.7); background: transparent; font-weight: 500;")
            meta_lbl.setObjectName("artistMeta")
            meta_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            info_layout.addWidget(meta_lbl)

        header_layout.addLayout(info_layout)

        # ── Action buttons (Centered) ──────────────────────────────────
        actions_row = QHBoxLayout()
        actions_row.setSpacing(16)
        actions_row.setContentsMargins(0, 16, 0, 16)
        actions_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        play_all_btn = QPushButton()
        play_all_btn.setIcon(Icon.icon("play_arrow", tokens.CURRENT.text_on_accent, 22))
        play_all_btn.setText("Reproducir")
        play_all_btn.setFont(AppFont.title(14))
        play_all_btn.setFixedHeight(52)
        play_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        play_all_btn.setStyleSheet(f\"\"\"
            QPushButton {{
                background: {tokens.CURRENT.accent};
                color: {tokens.CURRENT.text_on_accent};
                border: none;
                border-radius: 26px;
                padding: 0 32px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {tokens.CURRENT.accent_bright};
                transform: scale(1.05);
            }}
        \"\"\")
        play_all_btn.clicked.connect(lambda: self._play_first_song(data))
        actions_row.addWidget(play_all_btn)

        shuffle_btn = QPushButton()
        shuffle_btn.setIcon(Icon.icon("shuffle", tokens.CURRENT.text_primary, 22))
        shuffle_btn.setText("Aleatorio")
        shuffle_btn.setFont(AppFont.title(14))
        shuffle_btn.setFixedHeight(52)
        shuffle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        shuffle_btn.setStyleSheet(f\"\"\"
            QPushButton {{
                background: rgba(255, 255, 255, 0.1);
                color: {tokens.CURRENT.text_primary};
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 26px;
                padding: 0 32px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.15);
                border-color: rgba(255, 255, 255, 0.3);
            }}
        \"\"\")
        songs = data.get('songs', {}).get('results', [])
        if songs:
            import random
            shuffle_btn.clicked.connect(lambda: self._play_song(
                random.choice(songs), data.get('name', 'Unknown')
            ))
        actions_row.addWidget(shuffle_btn)
        
        header_layout.addLayout(actions_row)
        self.content_layout.addWidget(header_widget)"""
        
    content = content.replace(old_display, new_display)
    
    old_load = """    async def _load_cover(self, url: str):
        try:
            path = await _image_cache.download(url)
            import shiboken6
            if not shiboken6.isValid(self) or not shiboken6.isValid(self.cover):
                return
            if path:
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        200, 200,
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.cover.setPixmap(scaled)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error loading cover: {e}")"""
            
    new_load = """    async def _load_cover(self, url: str):
        try:
            path = await _image_cache.download(url)
            import shiboken6
            if not shiboken6.isValid(self) or not shiboken6.isValid(self.cover):
                return
            if path:
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    # Set background
                    bg_scaled = pixmap.scaled(
                        self.width() or 1000, 400,
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.bg_image.setPixmap(bg_scaled)
                    
                    # Create circular avatar
                    size = 200
                    scaled = pixmap.scaled(
                        size, size,
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    x = (scaled.width() - size) // 2
                    y = (scaled.height() - size) // 2
                    cropped = scaled.copy(x, y, size, size)
                    
                    circular = QPixmap(size, size)
                    circular.fill(Qt.GlobalColor.transparent)
                    painter = QPainter()
                    if painter.begin(circular):
                        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                        path_clip = QPainterPath()
                        from PySide6.QtCore import QRectF
                        path_clip.addEllipse(QRectF(0, 0, size, size))
                        painter.setClipPath(path_clip)
                        painter.drawPixmap(0, 0, cropped)
                        painter.end()
                        
                    self.cover.setPixmap(circular)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error loading cover: {e}")"""
            
    content = content.replace(old_load, new_load)

    with open('src/pyrolist/ui/screens/artist.py', 'w') as f:
        f.write(content)

patch()
