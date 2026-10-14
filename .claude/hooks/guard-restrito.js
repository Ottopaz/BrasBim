// Clean-room guard: bloqueia ferramentas que ACESSEM a pasta restrita (material de engenharia reversa).
// Verifica só caminhos e comandos — não o texto que está sendo escrito — para que documentos
// possam mencionar a regra. O nome é montado em partes para que este próprio arquivo possa ser editado.
// Saída com código 2 => Claude Code bloqueia a chamada e mostra o motivo ao modelo.
const DIR = "_restr" + "ito";
const pattern = new RegExp(DIR, "i");

let raw = "";
process.stdin.on("data", (c) => (raw += c));
process.stdin.on("end", () => {
  let payload;
  try {
    payload = JSON.parse(raw);
  } catch {
    process.exit(0);
  }
  const i = payload.tool_input || {};
  // Campos que indicam ACESSO a arquivos ou execução — não conteúdo escrito.
  const accessed = [i.command, i.file_path, i.notebook_path, i.path, i.pattern, i.glob]
    .filter((v) => typeof v === "string")
    .join("\n");
  if (pattern.test(accessed)) {
    process.stderr.write(
      `BLOQUEADO (clean-room): a pasta ${DIR}/ contém material de engenharia reversa e não pode ser ` +
        "acessada no BrasBim. Use apenas fontes públicas (cleanroom/FONTES.md)."
    );
    process.exit(2);
  }
  process.exit(0);
});
