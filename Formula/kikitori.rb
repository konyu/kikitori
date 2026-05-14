class Kikitori < Formula
  include Language::Python::Virtualenv

  desc "macOS menu bar voice-to-text tool with overlay UI"
  homepage "https://github.com/konyu/kikitori"
  url "https://github.com/konyu/kikitori/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "c494f62479cf3881979a9afaac70bad52f4b873433c6eae1a20053a72a72765a"
  license "MIT"

  depends_on "python@3.14"
  depends_on "ffmpeg"
  depends_on "portaudio"

  resource "mlx-whisper" do
    url "https://files.pythonhosted.org/packages/source/m/mlx-whisper/mlx-whisper-0.1.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "sounddevice" do
    url "https://files.pythonhosted.org/packages/source/s/sounddevice/sounddevice-0.4.6.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "numpy" do
    url "https://files.pythonhosted.org/packages/source/n/numpy/numpy-1.26.4.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "pynput" do
    url "https://files.pythonhosted.org/packages/source/p/pynput/pynput-1.7.6.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "pyperclip" do
    url "https://files.pythonhosted.org/packages/source/p/pyperclip/pyperclip-1.8.2.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "PySide6" do
    url "https://files.pythonhosted.org/packages/source/P/PySide6/PySide6-6.7.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "pyyaml" do
    url "https://files.pythonhosted.org/packages/source/p/pyyaml/pyyaml-6.0.1.tar.gz"
    sha256 "PLACEHOLDER"
  end

  def install
    venv = virtualenv_create(libexec, "python3.14")
    venv.pip_install resources
    venv.pip_install buildpath

    # ランチャースクリプト
    (bin/"kikitori").write_env_script libexec/"bin/python", libexec/"bin/kikitori"
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
