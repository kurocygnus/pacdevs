# PacDevs - atalhos de execução e empacotamento.
#
#   make run        roda o jogo direto do código (python3 main.py)
#   make appimage   gera dist/PacDevs-<arquitetura>.AppImage
#   make clean      remove arquivos gerados
#
# O AppImage é feito com PyInstaller + appimagetool (baixado automaticamente).
# Ele leva o Python e o pygame dentro, mas depende da glibc da máquina onde foi
# gerado: para rodar em distros mais antigas, gere-o numa distro antiga.

APP_NAME := PacDevs
BIN_NAME := pacdevs
ARCH     := $(shell uname -m)
PYTHON   ?= python3

VENV      := .venv-build
VPY       := $(VENV)/bin/python
BUILD_DIR := build
DIST_DIR  := dist
BUNDLE    := $(BUILD_DIR)/pyinstaller/$(BIN_NAME)
APPDIR    := $(BUILD_DIR)/$(APP_NAME).AppDir
APPIMAGE  := $(DIST_DIR)/$(APP_NAME)-$(ARCH).AppImage

APPIMAGETOOL     := $(BUILD_DIR)/appimagetool-$(ARCH).AppImage
APPIMAGETOOL_URL := https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$(ARCH).AppImage

SOURCES := $(wildcard *.py) $(shell find assets -type f)

.PHONY: help run appimage lint clean distclean
.DEFAULT_GOAL := help

help:
	@echo "make run        - roda o jogo (python3 main.py)"
	@echo "make appimage   - gera $(APPIMAGE)"
	@echo "make lint       - roda o pylint como no CI"
	@echo "make clean      - remove build/ e dist/"
	@echo "make distclean  - clean + remove o ambiente virtual $(VENV)"

run:
	$(PYTHON) main.py

# Ambiente virtual só para o build (pygame + PyInstaller)
$(VENV)/.ok: requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(VPY) -m pip install --upgrade pip
	$(VPY) -m pip install -r requirements.txt pyinstaller
	touch $@

# Pasta com o Python, o pygame e os assets embutidos
$(BUNDLE)/$(BIN_NAME): $(SOURCES) $(VENV)/.ok
	$(VPY) -m PyInstaller --noconfirm --clean --name $(BIN_NAME) \
		--distpath $(BUILD_DIR)/pyinstaller \
		--workpath $(BUILD_DIR)/pyinstaller-work \
		--specpath $(BUILD_DIR) \
		--add-data "$(CURDIR)/assets:assets" \
		$(CURDIR)/main.py

$(APPIMAGETOOL):
	mkdir -p $(BUILD_DIR)
	curl -fL --retry 3 -o $@ $(APPIMAGETOOL_URL)
	chmod +x $@

appimage: $(APPIMAGE)

$(APPIMAGE): $(BUNDLE)/$(BIN_NAME) $(APPIMAGETOOL) packaging/AppRun packaging/$(BIN_NAME).desktop assets/pacman.png
	rm -rf $(APPDIR)
	mkdir -p $(APPDIR)/usr/bin $(DIST_DIR)
	cp -a $(BUNDLE) $(APPDIR)/usr/bin/
	install -m 755 packaging/AppRun $(APPDIR)/AppRun
	cp packaging/$(BIN_NAME).desktop $(APPDIR)/
	SDL_VIDEODRIVER=dummy $(VPY) -c "import pygame; pygame.image.save(pygame.transform.smoothscale(pygame.image.load('assets/pacman.png'), (256, 256)), '$(APPDIR)/$(BIN_NAME).png')"
	ln -sf $(BIN_NAME).png $(APPDIR)/.DirIcon
	# --appimage-extract-and-run dispensa o FUSE (útil em containers e CI)
	ARCH=$(ARCH) $(APPIMAGETOOL) --appimage-extract-and-run $(APPDIR) $@
	@echo "AppImage gerado em $@"

lint: $(VENV)/.ok
	$(VPY) -m pip install --quiet pylint
	$(VPY) -m pylint $$(git ls-files '*.py')

clean:
	rm -rf $(BUILD_DIR) $(DIST_DIR)

distclean: clean
	rm -rf $(VENV)
