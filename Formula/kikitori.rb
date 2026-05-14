class Kikitori < Formula
  desc "macOS menu bar voice-to-text tool with overlay UI"
  homepage "https://github.com/konyu/kikitori"
  url "https://github.com/konyu/kikitori/archive/refs/tags/v1.0.2.tar.gz"
  sha256 "7b7b7a5130fd13aeb357944fac6f90c56f340ee4b543498f102c0a40fdde2eed"
  license "MIT"

  depends_on "python@3.14"
  depends_on "ffmpeg"
  depends_on "portaudio"

  def install
    # 手動でvenv作成（pip付き）
    system Formula["python@3.14"].opt_bin/"python3.14", "-m", "venv", libexec

    # pip アップグレード
    system libexec/"bin/pip", "install", "--upgrade", "pip"

    # 依存関係インストール
    system libexec/"bin/pip", "install", "-r", buildpath/"requirements.txt"

    # アプリケーションファイルをコピー
    libexec.install Dir["*"]

    # ランチャースクリプト
    (bin/"kikitori").write <<~EOS
      #!/bin/bash
      exec "#{libexec}/bin/python" "#{libexec}/pyside_main.py" "$@"
    EOS
  end

  service do
    run [opt_bin/"kikitori"]
    keep_alive true
    log_path var/"log/kikitori.log"
    error_log_path var/"log/kikitori.error.log"
  end

  test do
    system bin/"kikitori", "--version"
  end
end
