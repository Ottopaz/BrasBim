# SPDX-License-Identifier: GPL-3.0-or-later
"""Assistente: anexar imagem e ver o objeto criado
(spec/ui/54-assistente-foto-e-objeto-novo.md): AF01–AF03, AF07 e AF08. Qt sem tela e
sem chamar IA nenhuma."""

import base64
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from conftest import snapshot
from PySide6.QtCore import QByteArray, QMimeData, Qt, QUrl
from PySide6.QtGui import QColor, QImage

from brasbim.core.objects import elements as objects
from brasbim.ui import assistant as ai
from brasbim.ui import icons


def _image(width=200, height=120, alpha=False, color="#c0392b") -> QImage:
    image = QImage(width, height, QImage.Format_ARGB32 if alpha else QImage.Format_RGB32)
    image.fill(QColor(0, 0, 0, 0) if alpha else QColor(color))
    return image


def _file(tmp_path, name, image=None) -> str:
    path = tmp_path / name
    (image or _image()).save(str(path))
    return str(path)


def _decode(data: bytes) -> QImage:
    image = QImage()
    assert image.loadFromData(data)
    return image


def _log(panel) -> list[str]:
    return [panel.log.item(i).text() for i in range(panel.log.count())]


def test_af01_anexar_por_arquivo_colar_e_arrastar(window, tmp_path):
    a = window.assistant
    assert "image" in icons.names() and not a.attach_button.icon().isNull()
    assert "enviada à IA" in a.attach_button.toolTip()
    assert a.attach_strip.isHidden() and a.attachments == []
    # arquivo
    assert a.attach_files([_file(tmp_path, "fogao.png")]) == 1
    assert not a.attach_strip.isHidden() and len(a.remove_buttons) == 1
    assert a.attachments[0].name == "fogao.png"
    assert max(a.attachments[0].thumb.width(), a.attachments[0].thumb.height()) == ai.THUMB
    # colar uma imagem (Ctrl+V no campo do pedido): anexa, não escreve texto
    mime = QMimeData()
    mime.setImageData(_image())
    assert a.prompt.canInsertFromMimeData(mime)
    a.prompt.insertFromMimeData(mime)
    assert len(a.attachments) == 2 and a.prompt.toPlainText() == ""
    # arrastar um arquivo (colar um arquivo copiado dá no mesmo)
    drop = QMimeData()
    drop.setUrls([QUrl.fromLocalFile(_file(tmp_path, "lado.jpg"))])
    assert a.take_mime(drop) and len(a.attachments) == 3
    # texto colado continua texto
    text = QMimeData()
    text.setText("um fogão")
    assert not a.take_mime(text)
    a.prompt.insertFromMimeData(text)
    assert a.prompt.toPlainText() == "um fogão" and len(a.attachments) == 3
    a.prompt.clear()
    # o × tira a imagem
    a.remove_buttons[1].click()
    assert [x.name for x in a.attachments] == ["fogao.png", "lado.jpg"]
    assert len(a.remove_buttons) == 2
    # a quinta é recusada; arquivo que não é imagem e arquivo que não abre também
    for i in range(2):
        assert a.attach_image(_image(), f"{i}.png")
    assert not a.attach_image(_image(), "quinta.png")
    assert _log(a)[-1] == "no máximo 4 imagens por pedido"
    a.remove_attachment(0)
    note = tmp_path / "medidas.txt"
    note.write_text("76 x 60", encoding="utf-8")
    broken = tmp_path / "quebrada.png"
    broken.write_bytes(b"isto nao e png")
    assert a.attach_files([str(note), str(broken)]) == 0
    assert _log(a)[-2:] == ["medidas.txt não é imagem PNG, JPEG ou WebP",
                            "não foi possível abrir quebrada.png"]
    assert len(a.attachments) == 3
    # outro projeto: os anexos não passam de um para outro
    window.session.new()
    assert a.attachments == [] and a.attach_strip.isHidden()


def test_af02_imagem_grande_e_reduzida():
    data, media = ai.prepare_image(_image(4000, 3000))
    assert media == "image/jpeg"
    small = _decode(data)
    assert (small.width(), small.height()) == (ai.MAX_IMAGE_SIDE, 1176)
    # com transparência continua PNG (e continua transparente)
    data, media = ai.prepare_image(_image(3000, 4000, alpha=True))
    assert media == "image/png" and data.startswith(b"\x89PNG")
    small = _decode(data)
    assert small.height() == ai.MAX_IMAGE_SIDE and small.hasAlphaChannel()
    # a pequena não é ampliada
    data, _ = ai.prepare_image(_image(200, 120))
    assert _decode(data).width() == 200


def test_af03_pedido_vai_como_mensagem_com_as_imagens(window):
    args = ai.ClaudeCode(program="claude").arguments("cfg.json")
    assert args[args.index("--input-format") + 1] == "stream-json"
    assert args[args.index("--tools") + 1] == ""  # continua sem terminal nem arquivos
    a = window.assistant
    # só texto
    message = json.loads(a.build_message("uma sala de 4 × 4"))
    assert message["type"] == "user" and message["message"]["role"] == "user"
    (block,) = message["message"]["content"]
    assert block["type"] == "text"
    assert block["text"].startswith("[BrasBim]")
    assert block["text"].endswith("uma sala de 4 × 4")
    # imagens antes do texto, em base64, com o tipo certo
    a.attach_image(_image(), "a.png")
    a.attach_image(_image(alpha=True), "b.png")
    message = a.build_message("crie este fogão, 76 × 60 × 85 cm", a.attachments)
    assert "\n" not in message  # uma linha só
    content = json.loads(message)["message"]["content"]
    assert [b["type"] for b in content] == ["image", "image", "text"]
    assert [b["source"]["media_type"] for b in content[:2]] == ["image/jpeg", "image/png"]
    assert all(b["source"]["type"] == "base64" for b in content[:2])
    assert not _decode(base64.b64decode(content[0]["source"]["data"])).isNull()
    assert content[2]["text"].endswith("crie este fogão, 76 × 60 × 85 cm")
    # só imagem: vai com o texto padrão
    content = json.loads(a.build_message("", a.attachments))["message"]["content"]
    assert content[-1]["text"].endswith(ai.ONLY_IMAGE_TEXT)


def _fogao():
    return {"name": "Fogão de teste", "category": "appliance",
            "params": [{"name": "largura", "value": 0.76},
                       {"name": "profundidade", "value": 0.60},
                       {"name": "altura", "value": 0.85}],
            "pieces": [{"kind": "box", "name": "Corpo", "width": "largura",
                        "depth": "profundidade", "height": "altura",
                        "material": "Eletrodoméstico"},
                       {"kind": "cylinder", "name": "Boca", "x": 0.2, "y": 0.2,
                        "z": "altura", "radius": 0.05, "height": 0.02, "material": "Inox",
                        "repeat": {"count": 2, "dx": 0.3}}]}


def test_af07_imagem_do_objeto(window):
    a = window.assistant
    assert "view_object" in a.registry.tools and not a.registry.tools["view_object"].changes
    made = a.execute("create_object", _fogao())
    assert not made["isError"], made
    before = snapshot(window.session.doc.ifc)
    result = a.execute("view_object", {"type": "Fogão de teste"})
    assert not result["isError"]
    picture, text = result["content"]
    assert picture["type"] == "image" and picture["mimeType"] == "image/png"
    image = _decode(base64.b64decode(picture["data"]))
    assert (image.width(), image.height()) == (840, 840)
    # as quatro vistas têm desenho: em cada quadro há o fundo, a peça e as linhas dela
    for cx, cy in ((0, 0), (420, 0), (0, 420), (420, 420)):
        colors = {image.pixel(cx + x, cy + y) for x in range(8, 412, 2)
                  for y in range(8, 372, 2)}
        assert len(colors) > 3
    info = json.loads(text["text"])
    assert info["tipo"] == "Fogão de teste"
    assert info["caixa"]["largura"] == pytest.approx(0.76)
    assert info["caixa"]["altura"] == pytest.approx(0.87)
    assert snapshot(window.session.doc.ifc) == before  # só olha
    assert _log(a)[-1] == "• Olhando o objeto"
    # o da biblioteca é visto sem ser carregado no projeto
    result = a.execute("view_object", {"type": "Fogão 4 bocas"})
    assert not result["isError"] and result["content"][0]["type"] == "image"
    assert json.loads(result["content"][1]["text"])["caixa"]["largura"] == pytest.approx(0.5)
    assert snapshot(window.session.doc.ifc) == before
    # objeto que não existe
    result = a.execute("view_object", {"type": "Geladeira de teste"})
    assert result["isError"] and "não está no projeto" in result["content"][0]["text"]


def test_af08_criar_corrigir_e_inserir_e_um_passo_de_desfazer(window):
    s, a = window.session, window.assistant
    before = snapshot(s.doc.ifc)
    n = len(s.history.undo_stack)
    a._prompt = "crie o fogão da foto"
    assert not a.execute("create_object", _fogao())["isError"]
    spec = _fogao()
    spec["pieces"].append({"kind": "box", "name": "Painel", "y": "profundidade - 0,05",
                           "z": "altura", "width": "largura", "depth": 0.05,
                           "height": 0.1, "material": "Inox"})
    fixed = a.execute("edit_object_definition",
                      {"object": "Fogão de teste", "pieces": spec["pieces"]})
    assert not fixed["isError"], fixed
    placed = a.execute("insert_object", {"type": "Fogão de teste", "at": [1.0, 2.0]})
    assert not placed["isError"], placed
    gid = json.loads(placed["content"][0]["text"])["id"]
    assert _log(a)[-3:] == ["• Criando objeto", "• Corrigindo objeto", "• Inserindo objeto"]
    assert objects.is_object(s.doc.get(gid))
    a._group()
    assert len(s.history.undo_stack) == n + 1
    assert s.history.undo_stack[-1].label == "Assistente: crie o fogão da foto"
    assert s.selection == {gid}  # o objeto criado fica selecionado
    window.undo()
    assert snapshot(s.doc.ifc) == before


def test_af03_pedido_enviado_mostra_as_miniaturas_e_limpa_os_anexos(window, monkeypatch):
    """Sem IA: o processo é trocado por um que só guarda o que recebeu."""
    a = window.assistant
    written = {}

    class FakeProcess:
        def __init__(self, parent=None):
            self.readyReadStandardOutput = self.finished = self.errorOccurred = self
        def connect(self, slot):
            pass
        def setProgram(self, program):
            written["program"] = program
        def setArguments(self, args):
            written["args"] = args
        def setWorkingDirectory(self, path):
            pass
        def start(self):
            pass
        def write(self, data):
            written["data"] = data
        def closeWriteChannel(self):
            written["closed"] = True
        def kill(self):
            pass
        def waitForFinished(self, ms):
            return True
        def readAllStandardOutput(self):
            return QByteArray()
        def readAllStandardError(self):
            return QByteArray()
        def exitCode(self):
            return 0
        def deleteLater(self):
            pass

    monkeypatch.setattr(ai, "QProcess", FakeProcess)
    a.connector = ai.ClaudeCode(program="claude")
    a.attach_image(_image(), "fogao.png")
    a.send()  # só imagem, sem texto
    try:
        assert written["closed"] and written["data"].endswith(b"\n")
        content = json.loads(written["data"].decode("utf-8"))["message"]["content"]
        assert [b["type"] for b in content] == ["image", "text"]
        assert content[1]["text"].endswith(ai.ONLY_IMAGE_TEXT)
        assert "--input-format" in written["args"]
        assert a.attachments == [] and a.attach_strip.isHidden()
        assert a.log.item(a.log.count() - 2).text() == "(imagem)"
        thumbs = a.log.item(a.log.count() - 1).data(Qt.DecorationRole)
        assert thumbs is not None and not thumbs.isNull()
    finally:
        a._done()
        a.shutdown()
    assert not a.running


def test_af02_foto_de_arquivo_e_reduzida_ao_anexar(window, tmp_path):
    a = window.assistant
    assert a.attach_files([_file(tmp_path, "grande.jpg", _image(3200, 2400))]) == 1
    sent = _decode(a.attachments[0].data)
    assert (sent.width(), sent.height()) == (ai.MAX_IMAGE_SIDE, 1176)
    a.remove_attachment(0)
