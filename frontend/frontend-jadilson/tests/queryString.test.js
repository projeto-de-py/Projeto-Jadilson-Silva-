import assert from "node:assert/strict";
import test from "node:test";

import { queryString } from "../src/data/queryString.js";

test("queryString omite vazios e preserva a ordem dos filtros", () => {
  assert.equal(
    queryString({ q: "Revisional", area: "", status: undefined, pagina: 2, limite: 100 }),
    "?q=Revisional&pagina=2&limite=100",
  );
});

test("queryString codifica acentos e caracteres especiais", () => {
  assert.equal(queryString({ q: "Ação & Contrato" }), "?q=A%C3%A7%C3%A3o+%26+Contrato");
});

test("queryString devolve string vazia quando não há filtros", () => {
  assert.equal(queryString(), "");
  assert.equal(queryString({ q: null, area: "" }), "");
});
