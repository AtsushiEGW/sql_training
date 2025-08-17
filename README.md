# フォルダ構成
your-project/
├─ docker-compose.yml
├─ docker/
│  └─ python/
│     └─ Dockerfile
├─ .devcontainer/
│  └─ devcontainer.json
├─ requirements.txt
├─ .env
└─ db/
   └─ init.sql   # 任意



dbt core と postgresql を使用してデータ分析基盤の構築をしています。
エディタは vscode です。
スタイルとして dbt のスタイルガイドを参考にします。
この環境でこのスタイルで開発を行うための、linter 等の設定はどの様にすればよいでしょうか。
 dbt のスタイルガイドとは以下のことです。

基本的方針、sql, python, jinja, yaml についてのガイドです
https://docs.getdbt.com/best-practices/how-we-style/1-how-we-style-our-dbt-models
https://docs.getdbt.com/best-practices/how-we-style/2-how-we-style-our-sql
https://docs.getdbt.com/best-practices/how-we-style/3-how-we-style-our-python
https://docs.getdbt.com/best-practices/how-we-style/4-how-we-style-our-jinja
https://docs.getdbt.com/best-practices/how-we-style/5-how-we-style-our-yaml




フォルダ構成
~/.dotfiles/
	- tmux/
    	- .tmux.conf
  	- zsh/
    	- .zshrc
	- .starship.toml
  	- Brewfile
  	- install_for_linux.sh
  	- install.sh


以下ファイルの中身
=== tmux/.tmux.conf ===
set -g escape-time 0
set -g prefix C-g
unbind C-b

bind \/ split-window -h
bind - split-window -v

=== zsh/.zshrc ===
# ~/.zshrc

# path
export PATH="$PATH:$HOME/.local/bin"

# 共通設定（ヒストリ、エイリアスなど）
HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=10000
setopt hist_ignore_dups
setopt share_history

alias ll='ls -la'
alias gs='git status'
alias ta='tmux attach -t'
alias tn='tmux new -s'
alias update='brew update && brew upgrade && brew cleanup'


# --- OS判定 ---
OS_TYPE="$(uname -s)"

if [ "$OS_TYPE" = "Darwin" ]; then
  # ======== macOS の場合 ========
  
  # Homebrew 環境をロード
  if command -v brew &>/dev/null; then
    eval "$(brew shellenv)"
  fi

  # starship（brewでインストール推奨）
  if command -v starship &>/dev/null; then
    eval "$(starship init zsh)"
  fi

  # fzf (Homebrew版)
  if [ -f "$(brew --prefix)/opt/fzf/shell/key-bindings.zsh" ]; then
    source "$(brew --prefix)/opt/fzf/shell/key-bindings.zsh"
  fi
  if [ -f "$(brew --prefix)/opt/fzf/shell/completion.zsh" ]; then
    source "$(brew --prefix)/opt/fzf/shell/completion.zsh"
  fi

  # zsh-autosuggestions（Homebrew）
  if [ -f "$(brew --prefix)/share/zsh-autosuggestions/zsh-autosuggestions.zsh" ]; then
    source "$(brew --prefix)/share/zsh-autosuggestions/zsh-autosuggestions.zsh"
  fi

  # zsh-syntax-highlighting（Homebrew）
  if [ -f "$(brew --prefix)/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh" ]; then
    source "$(brew --prefix)/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"
  fi

  # macOS固有のalias例
  alias clip='pbcopy'


else
  # ======== Linux の場合 ========

  # starship（手動インストールやcargo経由）
  export PATH="$HOME/.cargo/bin:$PATH"
  if command -v starship &>/dev/null; then
    eval "$(starship init zsh)"
  fi

  # fzf (aptや手動インストール)
  [ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

  # zsh-autosuggestions（Git clone版）
  if [ -f "$HOME/.zsh/zsh-autosuggestions/zsh-autosuggestions.zsh" ]; then
    source "$HOME/.zsh/zsh-autosuggestions/zsh-autosuggestions.zsh"
  fi

  # zsh-syntax-highlighting（Git clone版）
  if [ -f "$HOME/.zsh/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh" ]; then
    source "$HOME/.zsh/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"
  fi

  # Linux固有のalias例
  alias clip='xclip -selection clipboard'

fi

=== Brewfile ===
# Ambitious Vim-fork focused on extensibility and agility
brew "neovim"
# Alternative to backtracking PCRE-style regular expression engines
brew "re2"
# Cross-shell prompt for astronauts
brew "starship"
# Terminal multiplexer
brew "tmux"
# Display directories as trees (with optional color/HTML output)
brew "tree"
# Executes a program periodically, showing output fullscreen
brew "watch"
# Fish-like fast/unobtrusive autosuggestions for zsh
brew "zsh-autosuggestions"
# Fish shell like syntax highlighting for zsh
brew "zsh-syntax-highlighting"
cask "font-hackgen-nerd"
# uv (python env)
brew "uv"


# gui applications
cask "visual-studio-code"

# GPU-accelerated cross-platform terminal emulator and multiplexer
cask "wezterm"
vscode "aaron-bond.better-comments"
vscode "azemoh.one-monokai"
vscode "bierner.markdown-mermaid"
vscode "bodil.file-browser"
vscode "catppuccin.catppuccin-vsc"
vscode "christian-kohler.path-intellisense"
vscode "enkia.tokyo-night"
vscode "fabiospampinato.vscode-monokai-night"
vscode "github.github-vscode-theme"
vscode "jacobdufault.fuzzy-search"
vscode "kahole.magit"
vscode "ms-python.debugpy"
vscode "ms-python.python"
vscode "ms-python.vscode-pylance"
vscode "ms-toolsai.jupyter"
vscode "ms-toolsai.jupyter-keymap"
vscode "ms-toolsai.jupyter-renderers"
vscode "ms-toolsai.vscode-jupyter-cell-tags"
vscode "ms-toolsai.vscode-jupyter-slideshow"
vscode "rokoroku.vscode-theme-darcula"
vscode "sainnhe.everforest"
vscode "vscodevim.vim"
vscode "vspacecode.vspacecode"
vscode "vspacecode.whichkey"
vscode "yzhang.markdown-all-in-one"

# おすすめ
brew "bat"       # cat の代替（シンタックスハイライト付き）
brew "fd"        # find の代替（爆速）
brew "ripgrep"   # grep の代替（爆速）
brew "fzf"       # インクリメンタル検索ツール


=== install_for_linux.sh ===
#!/usr/bin/env bash
set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "$0")" && pwd)"

install_packages() {
  echo "→ 必要なパッケージをインストール…"
  if command -v apt-get &>/dev/null; then
    sudo apt-get update
    sudo apt-get install -y \
      git tmux fzf curl \
      fonts-powerline \
      # fzf, starship は公式リポジトリで新しければ
  elif command -v dnf &>/dev/null; then
    sudo dnf install -y \
      git zsh tmux fzf starship curl
  else
    echo "対応していないパッケージマネージャです。" >&2
    exit 1
  fi
}

install_zsh_plugins() {
  echo "→ Zsh プラグインをセットアップ…"
  ZSH_PLUGIN_DIR="$HOME/.zsh"
  mkdir -p "$ZSH_PLUGIN_DIR"
  # zsh-autosuggestions
  if [ ! -d "$ZSH_PLUGIN_DIR/zsh-autosuggestions" ]; then
    git clone --depth=1 https://github.com/zsh-users/zsh-autosuggestions.git \
      "$ZSH_PLUGIN_DIR/zsh-autosuggestions"
  fi
  # zsh-syntax-highlighting
  if [ ! -d "$ZSH_PLUGIN_DIR/zsh-syntax-highlighting" ]; then
    git clone --depth=1 https://github.com/zsh-users/zsh-syntax-highlighting.git \
      "$ZSH_PLUGIN_DIR/zsh-syntax-highlighting"
  fi
}

install_starship() {
  if ! command -v starship &>/dev/null; then
    echo "→ Starship をインストール…"
    curl -fsSL https://starship.rs/install.sh | sh -s -- -y
    export PATH="$HOME/.cargo/bin:$PATH"
  fi
}



link_dotfiles() {
  echo "→ dotfiles のシンボリックリンクを作成…"
  ln -sf "$DOTFILES_DIR/zsh/.zshrc" "$HOME/.zshrc"
  ln -sf "$DOTFILES_DIR/tmux/.tmux.conf" "$HOME/.tmux.conf"
}


main() {
  install_packages
  install_zsh_plugins
  install_starship
  link_dotfiles

  echo
  echo "🎉 Linux 環境（apt＋zsh＋starship＋tmux＋fzf＋プラグイン）がセットアップされました！"
}

main "$@"



=== install.sh ===
#!/bin/bash

DOTFILES="$HOME/.dotfiles"

echo "🔗 Setting up dotfiles..."

# Homebrew がインストールされてるか確認
if ! command -v brew &>/dev/null; then
    echo "🍺Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "🍺Homebrew found."
fi

# Brewfile をつかてアプリをインストール
echo "📦 Installing packages form Brewfile..."
brew bundle --file="$DOTFILES/Brewfile"
echo "✅ Brewfile installation complete."

# --------- ZSH ---------
if [ -f "$HOME/.zshrc" ] || [ -L "$HOME/.zshrc" ]; then
    mv "$HOME/.zshrc" "$HOME/.zshrc.bak"
    echo "🗂️  Backed up .zshrc to .zshrc.bak"
fi
ln -sf "$DOTFILES/zsh/.zshrc" "$HOME/.zshrc"
echo "✅ Linked .zshrc"

# --------- Neovim ---------
mkdir -p "$HOME/.config"
if [ -e "$HOME/.config/nvim" ] && [ ! -L "$HOME/.config/nvim" ]; then
    mv "$HOME/.config/nvim" "$HOME/.config/nvim.bak"
    echo "🗂️  Backed up .config/nvim to .config/nvim.bak"
fi
ln -snf "$DOTFILES/nvim" "$HOME/.config/nvim"
echo "✅ Linked Neovim config"

# --------- Starship ---------
ln -sf "$DOTFILES/starship.toml" "$HOME/.config/starship.toml"
echo "✅ Linked starship.toml"

# --------- Tmux ---------
if [ -f "$HOME/.tmux.conf" ] || [ -L "$HOME/.tmux.conf" ]; then
    mv "$HOME/.tmux.conf" "$HOME/.tmux.conf.bak"
    echo "🗂️  Backed up .tmux.conf to .tmux.conf.bak"
fi
ln -sf "$DOTFILES/tmux/.tmux.conf" "$HOME/.tmux.conf"
echo "✅ Linked .tmux.conf"

# --------- WezTerm ---------
ln -sf "$DOTFILES/wezterm/wezterm.lua" "$HOME/.wezterm.lua"
echo "✅ Linked wezterm.lua"

echo "🎉 All dotfiles linked successfully!"

#----------- VS Code ------------
VSCODE_USER="$HOME/Library/Application Support/Code/User"
mkdir -p "$VSCODE_USER"

ln -sf "$HOME/.dotfiles/vscode/settings.json" "$VSCODE_USER/settings.json"
ln -sf "$HOME/.dotfiles/vscode/keybindings.json" "$VSCODE_USER/keybindings.json"

if [ -d "$HOME/.dotfiles/vscode/snippets" ]; then
    ln -sfn "$HOME/.dotfiles/vscode/snippets" "$VSCODE_USER/snippets"
fi

echo "✅ Linked VSCode settings"

=== starship.toml ===
[aws]
symbol = "  "

[buf]
symbol = " "

[c]
symbol = " "

[cmake]
symbol = " "

[conda]
symbol = " "

[crystal]
symbol = " "

[dart]
symbol = " "

[directory]
read_only = " 󰌾"

[docker_context]
symbol = " "

[elixir]
symbol = " "

[elm]
symbol = " "

[fennel]
symbol = " "

[fossil_branch]
symbol = " "

[git_branch]
symbol = " "

[git_commit]
tag_symbol = '  '

[golang]
symbol = " "

[guix_shell]
symbol = " "

[haskell]
symbol = " "

[haxe]
symbol = " "

[hg_branch]
symbol = " "

[hostname]
ssh_symbol = " "

[java]
symbol = " "

[julia]
symbol = " "

[kotlin]
symbol = " "

[lua]
symbol = " "

[memory_usage]
symbol = "󰍛 "

[meson]
symbol = "󰔷 "

[nim]
symbol = "󰆥 "

[nix_shell]
symbol = " "

[nodejs]
symbol = " "

[ocaml]
symbol = " "

[os.symbols]
Alpaquita = " "
Alpine = " "
AlmaLinux = " "
Amazon = " "
Android = " "
Arch = " "
Artix = " "
CachyOS = " "
CentOS = " "
Debian = " "
DragonFly = " "
Emscripten = " "
EndeavourOS = " "
Fedora = " "
FreeBSD = " "
Garuda = "󰛓 "
Gentoo = " "
HardenedBSD = "󰞌 "
Illumos = "󰈸 "
Kali = " "
Linux = " "
Mabox = " "
Macos = " "
Manjaro = " "
Mariner = " "
MidnightBSD = " "
Mint = " "
NetBSD = " "
NixOS = " "
Nobara = " "
OpenBSD = "󰈺 "
openSUSE = " "
OracleLinux = "󰌷 "
Pop = " "
Raspbian = " "
Redhat = " "
RedHatEnterprise = " "
RockyLinux = " "
Redox = "󰀘 "
Solus = "󰠳 "
SUSE = " "
Ubuntu = " "
Unknown = " "
Void = " "
Windows = "󰍲 "

[package]
symbol = "󰏗 "

[perl]
symbol = " "

[php]
symbol = " "

[pijul_channel]
symbol = " "

[python]
symbol = " "

[rlang]
symbol = "󰟔 "

[ruby]
symbol = " "

[rust]
symbol = "󱘗 "

[scala]
symbol = " "

[swift]
symbol = " "

[zig]
symbol = " "

[gradle]
symbol = " "




