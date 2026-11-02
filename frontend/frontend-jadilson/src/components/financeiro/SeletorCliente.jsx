import { useState } from "react";
import { Button, Field, Input, Select } from "@/components/ui";
import { apiJson } from "@/lib/api";
import { useApiDados } from "@/hooks/useApiDados";
import { useSessao } from "@/context/sessao";
import { consultas } from "@/lib/consultas";

/**
 * Escolhe um cliente do BANCO (GET /api/clientes). Se o escritório ainda não tem o
 * cliente cadastrado no servidor, dá para criá-lo aqui mesmo (POST /api/clientes).
 */
export function SeletorCliente({ valor, aoMudar, id = "sel-cliente" }) {
  const { csrf } = useSessao();
  const { dados, carregando, erro, recarregar } = useApiDados("clientes?limite=100");
  const [criando, setCriando] = useState(false);
  const [form, setForm] = useState({ nome: "", cpf_cnpj: "", email: "", telefone: "" });
  const [salvando, setSalvando] = useState(false);
  const [erroForm, setErroForm] = useState("");

  const clientes = dados?.itens ?? [];

  // Com 14 dígitos (CNPJ), preenche o nome com a razão social da Receita (BrasilAPI).
  async function buscarCnpj() {
    setErroForm("");
    try {
      const empresa = await consultas.cnpj(form.cpf_cnpj);
      setForm((f) => ({ ...f, nome: f.nome || empresa.razao_social }));
    } catch (falha) {
      setErroForm(falha.message);
    }
  }
  const ehCnpj = form.cpf_cnpj.replace(/\D/g, "").length === 14;

  // Não é <form>: este seletor fica dentro de outros formulários (HTML não permite <form> aninhado).
  async function criar() {
    setSalvando(true);
    setErroForm("");
    try {
      const corpo = Object.fromEntries(Object.entries(form).filter(([, v]) => v.trim() !== ""));
      const novo = await apiJson("clientes", { method: "POST", csrf, body: corpo });
      recarregar();
      aoMudar(String(novo.id));
      setCriando(false);
      setForm({ nome: "", cpf_cnpj: "", email: "", telefone: "" });
    } catch (falha) {
      setErroForm(falha.message);
    } finally {
      setSalvando(false);
    }
  }

  if (erro) {
    return <p role="alert" className="text-status-vencido-ink text-13">{erro.message}</p>;
  }

  return (
    <div className="space-y-4">
      <Field label="Cliente" id={id} hint={clientes.length === 0 && !carregando ? "Nenhum cliente cadastrado no servidor ainda." : undefined}>
        <Select id={id} value={valor} onChange={(e) => aoMudar(e.target.value)} disabled={carregando}>
          <option value="">{carregando ? "Carregando…" : "Escolha um cliente…"}</option>
          {clientes.map((c) => (
            <option key={c.id} value={String(c.id)}>{c.nome}{c.cpf_cnpj ? ` · ${c.cpf_cnpj}` : ""}</option>
          ))}
        </Select>
      </Field>

      {!criando ? (
        <button type="button" onClick={() => setCriando(true)} className="text-13 text-primary hover:text-primary-hover font-medium">
          + Cadastrar novo cliente
        </button>
      ) : (
        <div className="border-border bg-surface-muted/40 space-y-4 rounded-card border p-4" onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); criar(); } }}>
          <Field label="Nome" id={`${id}-nome`}>
            <Input id={`${id}-nome`} required maxLength={160} value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="CPF ou CNPJ" id={`${id}-doc`} hint="Obrigatório para cobrança">
              <Input id={`${id}-doc`} maxLength={20} value={form.cpf_cnpj} onChange={(e) => setForm({ ...form, cpf_cnpj: e.target.value })} />
              {ehCnpj && (
                <button type="button" onClick={buscarCnpj} className="text-12 text-primary hover:text-primary-hover mt-2 font-medium">
                  Buscar razão social na Receita
                </button>
              )}
            </Field>
            <Field label="WhatsApp" id={`${id}-tel`} hint="Para receber o documento">
              <Input id={`${id}-tel`} maxLength={20} value={form.telefone} onChange={(e) => setForm({ ...form, telefone: e.target.value })} />
            </Field>
          </div>
          <Field label="E-mail" id={`${id}-email`}>
            <Input id={`${id}-email`} type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </Field>
          {erroForm && <p role="alert" className="text-status-vencido-ink text-13">{erroForm}</p>}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setCriando(false)}>Cancelar</Button>
            <Button onClick={criar} loading={salvando}>Salvar cliente</Button>
          </div>
        </div>
      )}
    </div>
  );
}
