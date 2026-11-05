## vendas_auto.py - lança vendas fictícias no Supabase (segunda a sábado)
## ideia: o programa olha a última data lançada e completa os dias que faltam até hoje
import os                                          ## lê as chaves guardadas no ambiente (Secrets do GitHub)
import random                                      ## faz os sorteios (o "globo de bingo")
from datetime import date, datetime, timedelta     ## trabalha com datas
from zoneinfo import ZoneInfo                      ## fuso do Brasil (o GitHub roda em UTC)
from supabase import create_client                 ## conexão com o Supabase

## ===================== CONFIGURAÇÕES (ajuste aqui) =====================
URL = os.environ["SUPABASE_URL"]                   ## endereço do projeto (guardado fora do código)
KEY = os.environ["SUPABASE_KEY"]                   ## chave do projeto (guardada fora do código)
FUSO = ZoneInfo("America/Sao_Paulo")               ## fuso usado para saber qual é "hoje"
VENDAS_POR_DIA = (35, 65)                          ## mínimo e máximo de vendas em um dia comum
FATOR_DIA = {5: 1.3}                               ## sábado vende 30% a mais (0 = segunda ... 5 = sábado)
FERIADOS = []                                      ## datas sem venda, no formato "AAAA-MM-DD"
PAGAMENTOS = {"pix": (50, 10), "debito": (30, 10), "dinheiro": (20, 0)}  ## forma: (peso, desconto %)
CARGO_VENDEDOR = "caixa"                           ## quem passa a venda: trecho do cargo em cad_colaboradores (ignora maiúsculas)
TAB_PRECO, COL_PRECO = "valor_vigente", "venda"    ## CONFIRA: tabela e coluna do preço vigente


## lê uma tabela inteira (o Supabase entrega no máximo 1000 linhas por vez)
def ler_tudo(sb, tabela, colunas):
    linhas, ini = [], 0                            ## linhas = tudo que já li; ini = onde começa o próximo lote
    while True:                                    ## repete até acabar a tabela
        lote = sb.table(tabela).select(colunas).range(ini, ini + 999).execute().data
        linhas += lote                             ## junta o lote ao total
        if len(lote) < 1000:                       ## lote incompleto = era o último
            break
        ini += 1000                                ## próximo lote
    return linhas


## sorteia os itens de UMA venda (cada produto tem bolinhas conforme o peso)
def sortear_itens(pesos, estoque, precos):
    ## só entram no globo produtos com estoque e com preço vigente
    ids = [p for p in pesos if estoque.get(p, 0) > 0 and p in precos]
    n = random.choices([1, 2, 3, 4], weights=[50, 30, 15, 5])[0]   ## quantos itens (1 é o mais comum)
    n = min(n, len(ids))                           ## não pode ter mais itens que produtos disponíveis
    itens = []                                     ## lista de (produto, quantidade)
    for _ in range(n):
        escolhido = random.choices(ids, weights=[pesos[i] for i in ids])[0]   ## tira uma bolinha
        ids.remove(escolhido)                      ## não repete o produto na mesma venda
        q = random.choices([1, 2, 3], weights=[80, 15, 5])[0]   ## quantidade, quase sempre 1
        q = min(q, estoque[escolhido])             ## nunca vende mais do que tem
        estoque[escolhido] -= q                    ## baixa o estoque só na memória deste programa
        itens.append((escolhido, q))
    return itens


def main():
    sb = create_client(URL, KEY)                   ## conecta no Supabase
    hoje = datetime.now(FUSO).date()               ## data de hoje no Brasil

    ## descobre a última data já lançada em vendas
    ult = sb.table("vendas").select("registro").order("registro", desc=True).limit(1).execute().data
    ultima = date.fromisoformat(ult[0]["registro"]) if ult else hoje - timedelta(days=1)
    if ultima >= hoje:                             ## já está tudo lançado (ex.: xlsx cobre até dez/2026)
        print("Nada a lançar.")
        return

    ## carrega o que precisa da base (1 vez só, para ficar rápido)
    pesos = {p["id_produto"]: float(p["peso_venda"] or 1) for p in ler_tudo(sb, "produtos", "id_produto,peso_venda")}
    precos = {p["id_produto"]: float(p[COL_PRECO]) for p in ler_tudo(sb, TAB_PRECO, f"id_produto,{COL_PRECO}")}
    estoque = {e["id_produto"]: e["quantidade"] for e in ler_tudo(sb, "estoque", "id_produto,quantidade")}

    ## vendedores: pega do cadastro quem tem cargo de vendedor, guardando a data de admissão
    vendedores = [(c["id_funcionario"], c["admissao"]) for c in ler_tudo(sb, "cad_colaboradores", "id_funcionario,cargo,admissao")
                  if CARGO_VENDEDOR in (c["cargo"] or "").lower()]
    ## clientes: pega do cadastro, guardando a data em que o cliente foi registrado
    clientes = [(c["id_cliente"], c["registro"]) for c in ler_tudo(sb, "clientes", "id_cliente,registro")]
    if not vendedores or not clientes:             ## sem vendedor ou cliente cadastrado, não dá para vender
        print("Cadastro de vendedores ou clientes vazio. Confira CARGO_VENDEDOR.")
        return

    ## descobre o último número de venda (formato F00001) para continuar a sequência
    uid = sb.table("vendas").select("id_venda").order("id_venda", desc=True).limit(1).execute().data
    num = int(uid[0]["id_venda"][1:]) if uid else 0

    novas = []                                     ## todas as linhas (itens) a gravar
    dia = ultima + timedelta(days=1)               ## começa no dia seguinte ao último lançado
    while dia <= hoje:
        d = dia.isoformat()                        ## data em texto, para comparar com o cadastro
        ## só quem já foi admitido / registrado até esse dia pode aparecer na venda
        vend_dia = [i for i, adm in vendedores if adm <= d]
        cli_dia = [i for i, reg in clientes if reg <= d]
        ## domingo (weekday 6) e feriado não têm venda; sem vendedor ou cliente no dia também não
        if dia.weekday() != 6 and d not in FERIADOS and vend_dia and cli_dia:
            qtd_vendas = int(random.randint(*VENDAS_POR_DIA) * FATOR_DIA.get(dia.weekday(), 1))
            ## sorteia os horários entre 08:00 e 19:00 e ordena, para o id acompanhar a hora
            segundos = sorted(random.randint(8 * 3600, 19 * 3600) for _ in range(qtd_vendas))
            for seg in segundos:
                itens = sortear_itens(pesos, estoque, precos)
                if not itens:                      ## sem produto disponível, pula a venda
                    continue
                num += 1
                id_venda = f"F{num:05d}"           ## F + 5 dígitos
                forma = random.choices(list(PAGAMENTOS), weights=[v[0] for v in PAGAMENTOS.values()])[0]
                desconto = PAGAMENTOS[forma][1]    ## desconto definido pela forma de pagamento
                hora = f"{seg // 3600:02d}:{seg % 3600 // 60:02d}:{seg % 60:02d}"
                cliente = random.choice(cli_dia)   ## mesmo cliente e vendedor em todos os itens da venda
                vendedor = random.choice(vend_dia)
                for id_prod, q in itens:
                    novas.append({
                        "id_venda": id_venda,
                        "id_produto": id_prod,
                        "quantidade": q,
                        "parcial": round(q * precos[id_prod], 2),   ## preço vigente do dia x quantidade
                        "pagamento": forma,
                        "desconto": desconto,
                        "registro": d,
                        "hora": hora,
                        "cliente": cliente,
                        "vendedor": vendedor,
                    })                             ## o total o banco calcula sozinho
        dia += timedelta(days=1)                   ## próximo dia

    ## grava no Supabase em lotes de 500 linhas
    for i in range(0, len(novas), 500):
        sb.table("vendas").insert(novas[i:i + 500]).execute()
    print(f"{len(novas)} linhas lançadas até {hoje}.")


if __name__ == "__main__":
    main()