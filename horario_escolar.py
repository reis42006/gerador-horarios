# /// script
# dependencies = ["marimo"]
# requires-python = ">=3.14"
# ///

import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Trabalho Prático: Gerador Automático de Horários

    ## Contexto e Modelação do Problema

    O objetivo deste trabalho é desenvolver um sistema automatizado para a geração de horários escolares. O problema consiste em atribuir aulas, turmas, professores e salas a tempos letivos (slots) ao longo da semana, garantindo que não existem conflitos de recursos.

    ---

    ## 1. Carregar os Dados

    Antes de começarmos a criar regras, precisamos de ler os ficheiros CSV que contêm toda a informação base do problema:
    - turmas.csv: Turmas da escola.
    - disciplinas.csv: Disciplinas, quem as leciona, carga semanal, se é de duplo periodo ou não e qual sala necessária para a disiciplina.
    - salas.csv: Salas disponíveis, os seus tipos e a quantidade.
    - disponibilidade_excecoes.csv: Dias e horas em que certos professores nao estão disponiveis.
    """)
    return


@app.cell
def _():
    import pandas as pd
    import pytest
    from ortools.sat.python import cp_model

    # Carregar os dados
    turmas = pd.read_csv("dados/turmas.csv")
    disciplinas = pd.read_csv("dados/disciplinas.csv")
    salas = pd.read_csv("dados/salas.csv")
    indisponibilidade = pd.read_csv("dados/disponibilidade_excecoes.csv")

    # Teste para confirmar se foi tudo lido 
    print("Dados carregados")
    print(f"Número de turmas: {len(turmas)}")
    print(f"Número de disciplinas: {len(disciplinas)}")
    print(f"Número de salas: {len(salas)}")
    return cp_model, disciplinas, indisponibilidade, pd, salas, turmas


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 2. Preparar o Modelo

    Para resolver este problema, optou-se pela utilização do solver CP-SAT da biblioteca Google OR-Tools

    Definimos também a dimensão do tempo na escola:
    - Dias da semana: 5 dias (segunda a sexta-feira).
    - Blocos de tempo (slots ou periodos): 5 periodos por dia.
    """)
    return


@app.cell
def _(cp_model):
    model = cp_model.CpModel()

    DIAS = range(5)
    SLOTS = range(5)
    return DIAS, SLOTS, model


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 3. Criação das Variáveis de Decisão ($x_{t, d, s, dia, slot}$)

    Para o computador conseguir decidir o horário, precisamos de criar interruptores (variáveis binárias) para cada combinação possível de turma, disciplina, sala, dia e hora.

    Usamos variáveis binárias $x_{t, d, s, dia, slot} \in \{0, 1\}$ com a seguinte lógica:

    $$x_{t, d, s, dia, slot} = 1 \quad \iff \quad \text{A turma } t \text{ tem aula de } d \text{ na sala } s, \text{ no } dia \text{ e } slot.$$

    Se a variável for 0, apenas significa que a aula em questão não acontece nesse momento e local.
    """)
    return


@app.cell
def _(DIAS, SLOTS, disciplinas, model, salas, turmas):
    aulas = {}

    for i, turma in turmas.iterrows():
        t_id = turma["turma"]  

        for j, disc in disciplinas.iterrows():
            d_id = disc["disciplina"]  

            for k, sala in salas.iterrows():
                s_id = sala["sala"]  

                for dia in DIAS:
                    for slot in SLOTS:

                        nome_var = f"x_{t_id}_{d_id}_{s_id}_{dia}_{slot}"

                        aulas[(t_id, d_id, s_id, dia, slot)] = model.NewBoolVar(nome_var)
    return (aulas,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 4. Restrição R1: Sem Sobreposição de Aulas por Turma

    Uma regra fundamental para o horário funcionar é que uma turma não pode estar em dois sítios ao mesmo tempo.

    Ou seja, para cada turma, em cada dia e em cada slot temporal, a soma de todas as aulas possíveis (independentemente da disciplina ou da sala) não pode ser superior a 1:

    $$\forall_{t \in \text{Turmas}}, \, \forall_{dia \in \text{DIAS}}, \, \forall_{slot \in \text{SLOTS}} \cdot \quad \sum_{d, \, s} x_{t, d, s, dia, slot} \le 1$$

    Isto afirma que a turma tem no máximo 1 aula por bloco de tempo (ou 0, caso esteja livre nesse bloco).
    """)
    return


@app.cell
def _(DIAS, SLOTS, aulas, disciplinas, model, salas, turmas):
    # Restrição R1 -- Uma turma não pode ter duas aulas em simultâneo.

    for i_r1, turma_r1 in turmas.iterrows():
        t_r1 = turma_r1["turma"]

        for dia_r1 in DIAS:
            for slot_r1 in SLOTS:
                model.Add(
                    sum(
                        aulas[(t_r1, disc["disciplina"], sala["sala"], dia_r1, slot_r1)]
                        for j_r1, disc in disciplinas.iterrows()
                        for k_r1, sala in salas.iterrows()
                        if (t_r1, disc["disciplina"], sala["sala"], dia_r1, slot_r1) in aulas
                    ) <= 1)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 5. Restrição R2: Cumprimento da Carga Horária Semanal

    Cada disciplina tem um número obrigatório de aulas por semana definido no ficheiro disciplinas.csv. O sistema precisa de garantir que não há aulas a mais ou em falta.

    Para cada turma $t$ e para cada disciplina $d$, a soma de todas as alocações dessa disciplina ao longo de todos os dias, *slots* e salas tem de ser exatamente igual à carga semanal exigida:

    $$\forall_{t \in \text{Turmas}}, \, \forall_{d \in \text{Disciplinas}} \cdot \quad \sum_{s, \, dia, \, slot} x_{t, d, s, dia, slot} = \text{CargaSemanal}_{d}$$

    Garantindo, assim, que o plano de cada turma é cumprido ao longo da semana.
    """)
    return


@app.cell
def _(DIAS, SLOTS, aulas, disciplinas, model, salas, turmas):
    # Restrição R2 -- Cada disciplina cumpre exatamente a carga semanal definida em disciplinas.csv, para cada turma
    for j_r2, turma_r2 in turmas.iterrows():
        t_r2 = turma_r2["turma"]

        for i_r2, disc_r2 in disciplinas.iterrows():
            d_r2 = disc_r2["disciplina"]

            carga_exigida = disc_r2["carga_semanal"]

            model.Add(
                sum(
                    aulas[(t_r2,d_r2,sala_r2["sala"],dia_r2,slot_r2)]
                    for k_r2, sala_r2 in salas.iterrows()
                    for dia_r2 in DIAS
                    for slot_r2 in SLOTS
                    if (t_r2, d_r2, sala_r2["sala"], dia_r2, slot_r2) in aulas
                ) == carga_exigida
            )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 6. Restrição R3: Limite Diário de Aulas por Disciplina

    Define-se que uma turma não deve ter mais do que 1 aula por dia da mesma disciplina.

    A única exceção aplica-se às disciplinas marcadas como sendo de duplo período (bloco de 2 tempos seguidos), permitindo-se, nesses casos específicos, até 2 tempos no mesmo dia.

    Definindo $M_d \in \{1, 2\}$ como o limite máximo de blocos diários permitido para a disciplina $d$:

    $$\forall_{t \in \text{Turmas}}, \, \forall_{d \in \text{Disciplinas}}, \, \forall_{dia \in \text{DIAS}} \cdot \quad \sum_{s, \, slot} x_{t, d, s, dia, slot} \le M_d$$
    """)
    return


@app.cell
def _(DIAS, SLOTS, aulas, disciplinas, model, salas, turmas):
    # Restrição R3 -- No máximo uma aula da mesma disciplina por dia, por turma — exceto disciplinas de duplo período (ver R4), em que o bloco de 2 tempos conta como uma só ocorrência nesse dia

    for j_r3 , turma_r3 in turmas.iterrows():
        t_r3 = turma_r3["turma"]

        for i_r3, disc_r3 in disciplinas.iterrows():
            d_r3 = disc_r3["disciplina"]
            s_duplo = str(disc_r3["duplo_periodo"]).strip().lower() == "sim"

            max_aulas = 2 if s_duplo else 1
            for dia_r3 in DIAS:
                model.Add(
                    sum(
                        aulas[(t_r3,d_r3,sala_r3["sala"],dia_r3,slot_r3)]
                        for k_r3, sala_r3 in salas.iterrows()
                        for slot_r3 in SLOTS
                        if (t_r3, d_r3, sala_r3["sala"], dia_r3, slot_r3) in aulas
                    )<= max_aulas
                )
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ##7.  Restrição R4: Disciplinas de Duplo Período (Tempos Consecutivos)

    Nas disciplinas assinaladas com duplo_periodo = sim, as aulas têm de ser dadas em blocos contínuos de 2 tempos no mesmo dia.

    ---

    ### 1. Mapeamento das Aulas (has_aula)
    Para cada combinação de turma, disciplina, dia e slot, agregamos as salas numa variável binária que indica se há aula nesse bloco:

    $$y_{t, d, dia, slot} = \sum_{sala} x_{t, d, sala, dia, slot}$$

    * has_aula = 1: Existe aula no slot (independentemente da sala).
    * has_aula = 0: Não há aula nesse slot.

    ---

    ### 2. Obrigatoriedade de 2 Tempos por Dia
    Garante-se que a disciplina nunca é dada em apenas 1 tempo isolado. Através de uma variável binária de ocorrência diária ($O \in \{0, 1\}$):

    * Se a disciplina ocorre no dia: É obrigatório ter exatamente 2 tempos.
    * Se não ocorre: Tem 0 tempos.

    $$\sum_{slot} y_{t, d, dia, slot} = 2 \cdot O_{t,d,dia}$$

    ---

    ### 3. Conectividade dos Tempos (Adjacência)
    Para garantir que os 2 tempos ficam colados, definem-se três regras importantes:

    1. Início do dia ($slot = 0$): Se houver aula no 1º tempo, o 2º tempo é obrigatório.
       $$y_{slot_0} \implies y_{slot_1}$$

    2. Fim do dia ($slot = 4$): Se houver aula no último tempo, o penúltimo é obrigatório.
       $$y_{slot_4} \implies y_{slot_3}$$

    3. Meio do dia ($slot \in \{1, 2, 3\}$): Ter aula num tempo intermédio obriga a que o outro tempo esteja colado imediatamente antes ou imediatamente depois.
       $$y_{slot_s} \implies (y_{slot_{s-1}} \lor y_{slot_{s+1}})$$
    """)
    return


@app.cell
def _(DIAS, SLOTS, aulas, disciplinas, model, salas, turmas):
    # Restrição R4 -- Disciplinas marcadas duplo_periodo=sim só podem ser dadas em blocos de 2 tempos consecutivos, no mesmo dia (nunca um tempo isolado)

    for j_r4, turma_r4 in turmas.iterrows():
        t_r4 = turma_r4["turma"]

        for i_r4, disc_r4 in disciplinas.iterrows():
            d_r4 = disc_r4["disciplina"]
            s_duplo_r4 = str(disc_r4["duplo_periodo"]).strip().lower() == "sim"

            if s_duplo_r4:

                for dia_r4 in DIAS:
                    aulas_slot = []

 
                    for slot_r4 in SLOTS:
                        has_aula = model.NewBoolVar(f"has_aula_{t_r4}_{d_r4}_{dia_r4}_{slot_r4}")

                        model.Add(
                            sum(
                                aulas[(t_r4, d_r4, sala["sala"], dia_r4, slot_r4)]
                                for k, sala in salas.iterrows()
                            ) == has_aula
                        )

                        aulas_slot.append(has_aula)

                    ocorre_no_dia = model.NewBoolVar(f"ocorre_{t_r4}_{d_r4}_{dia_r4}")
                    model.Add(sum(aulas_slot) == 2).OnlyEnforceIf(ocorre_no_dia)
                    model.Add(sum(aulas_slot) == 0).OnlyEnforceIf(ocorre_no_dia.Not())

                    model.AddImplication(aulas_slot[0], aulas_slot[1])

                    model.AddImplication(aulas_slot[4], aulas_slot[3])
    
                    for s in range(1, 4):
                        model.AddBoolOr([aulas_slot[s - 1], aulas_slot[s + 1]]).OnlyEnforceIf(aulas_slot[s])
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 8. Restrição R5: Sem Sobreposição de Horário para Professores


    Para cada professor $p$, em cada dia e em cada slot, a soma de todas as aulas em que $p$ é o professor responsável (considerando todas as turmas, disciplinas atribuídas e salas) não pode exceder 1:

    $$\forall_{p \in \text{Professores}}, \, \forall_{dia \in \text{DIAS}}, \, \forall_{slot \in \text{SLOTS}} \cdot \quad \sum_{d \in D_p, \, t, \, s} x_{t, d, s, dia, slot} \le 1$$

    onde $D_p$ representa o conjunto de disciplinas lecionadas pelo professor $p$.
    """)
    return


@app.cell
def _(DIAS, SLOTS, aulas, disciplinas, model, salas, turmas):
    # Restrição R5 -- Um professor não pode dar duas aulas em simultâneo, mesmo que sejam a turmas ou disciplinas diferentes

    professores = disciplinas["professor"].dropna().unique()

    for prof_r5 in professores:
        disc_prof = disciplinas[disciplinas["professor"] == prof_r5]

        for dia_r5 in DIAS:
            for slot_r5 in SLOTS:
                aulas_prof = []

                for i_r5, disc_r5 in disc_prof.iterrows():
                    d_r5 = disc_r5["disciplina"]

                    for l_r5, turma_r5 in turmas.iterrows():
                        t_r5 = turma_r5["turma"]

                        for p_r5, salas_r5 in salas.iterrows():
                            s_r5 = salas_r5["sala"]

                            chave_r5 = (t_r5, d_r5, s_r5, dia_r5, slot_r5)


                            if chave_r5 in aulas:
                                aulas_prof.append(aulas[chave_r5])

   
                if aulas_prof:
                    model.Add(sum(aulas_prof) <= 1)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 9. Restrição R6: Indisponibilidades dos Professores

    As exceções e impedimentos de horário estão registados no ficheiro disponibilidade_excecoes.csv.

    Para garantir que nenhum professor é colocado num momento de indisponibilidade, forçamos as variáveis binárias correspondentes a zero:

    $$\forall (p, dia, slot) \in \text{Indisponibilidades}, \, \forall d \in D_p, \, \forall t, \, \forall s \cdot \quad x_{t, d, s, dia, slot} = 0$$

    Em termos práticos, se o professor $p$ estiver indisponível no $dia$ e $slot$ indicados na tabela de exceções, qualquer aula associada a esse professor nesse bloco temporal é sumariamente proibida.
    """)
    return


@app.cell
def _(aulas, disciplinas, indisponibilidade, model, salas, turmas):
    # Restrição R6 -- Um professor só pode dar aulas nos tempos em que está disponível (disponibilidade_excecoes.csv)

    mapa_dias = {
        "Seg": 1,
        "Ter": 2,
        "Qua": 3,
        "Qui": 4,
        "Sex": 5
    }

    for j_r6, exc in indisponibilidade.iterrows():
        prof_exc = exc["professor"]

        dia_exc = mapa_dias[str(exc["dia"]).strip()]


        periodo_exc = int(exc["periodo"])

        disc_prof_r6 = disciplinas[disciplinas["professor"] == prof_exc]

        for k_r6, disc_r6 in disc_prof_r6.iterrows():
            d_r6 = disc_r6["disciplina"]

            for l_r6, turma_r6 in turmas.iterrows():
                t_r6 = turma_r6["turma"]

                for p_r6, salas_r6 in salas.iterrows():
                    s_r6 = salas_r6["sala"]

                    chave = (t_r6, d_r6, s_r6, dia_exc, periodo_exc)

                    if chave in aulas:
                        model.Add(aulas[chave] == 0)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## 10. Restrição R7: Compatibilidade e Capacidade das Salas de Aula


    A regra divide-se em duas partes:

    1. Compatibilidade de Tipo de Sala: Se a disciplina $d$ e a sala $s$ forem incompatíveis (por exemplo, uma disciplina normal numa sala especial, ou vice-versa), a alocação é proibida:
       $$\forall (t, d, s, dia, slot) \text{ incompatíveis} \cdot \quad x_{t, d, s, dia, slot} = 0$$

    2. Capacidade: Em cada instante ($dia$ e $slot$), o total de aulas a decorrer na sala $s$ não pode ultrapassar a quantidade  disponível $Q_s$ definida em salas.csv:
       $$\forall_{s \in \text{Salas}}, \, \forall_{dia \in \text{DIAS}}, \, \forall_{slot \in \text{SLOTS}} \cdot \quad \sum_{t, \, d} x_{t, d, s, dia, slot} \le Q_s$$
    """)
    return


@app.cell
def _(DIAS, SLOTS, aulas, disciplinas, model, pd, salas, turmas):
    # Restrição R7 -- Cada aula ocupa uma sala. Disciplinas com sala_especial só podem usar salas desse tipo; as restantes usam salas normal. Em nenhum tempo o número de aulas a decorrer num tipo de sala pode exceder a quantidade desse tipo definida em salas.csv

    for j_r7, disc_r7 in disciplinas.iterrows():
        d_r7 = disc_r7["disciplina"]

        sala_esp = str(disc_r7["sala_especial"]).strip() if pd.notna(disc_r7["sala_especial"]) else ""
        is_especial = len(sala_esp) > 0 and sala_esp.lower() != "nan"

        for k_7, sala_r7 in salas.iterrows():
            s_r7 = sala_r7["sala"]
            tipo_sala = (sala_r7["tipo"]).strip().lower()

            nao_compativel = False
            if is_especial and s_r7 != sala_esp:
                nao_compativel = True
            if not is_especial and tipo_sala != "normal":
                nao_compativel = True

            if nao_compativel:
                for y_r7, turma_r7 in turmas.iterrows():
                    t_r7 = turma_r7["turma"]
                    for dia_r7 in DIAS:
                        for slot_r7 in SLOTS:
                            chave_r7 = (t_r7,d_r7,s_r7,dia_r7,slot_r7)
                            if chave_r7 in aulas:
                                model.Add(aulas[chave_r7] == 0 )

    for k_r7, sala_r7 in salas.iterrows():
        s_r7 = sala_r7["sala"]
        qtd_max = int(sala_r7["quantidade"])

        for dia_r7 in DIAS:
            for slot_r7 in SLOTS:
                aulas_na_sala = []
                for y_r7, turma_r7 in turmas.iterrows():
                    t_r7 = turma_r7["turma"]
                    for j_r7, disc_r7 in disciplinas.iterrows():
                        d_r7 = disc_r7["disciplina"]
                        chave_r7 = (t_r7,d_r7,s_r7,dia_r7,slot_r7)
                        if chave_r7 in aulas:
                            aulas_na_sala.append(aulas[chave_r7])
            
                if aulas_na_sala:
                    model.Add(sum(aulas_na_sala)<= qtd_max)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    #O1. Minimizar o número total de "buracos" no horário de cada professor

    Um buraco é um tempo livre, no meio do dia, entre a primeira e a última aula desse professor nesse dia.

    A implementação deste objetivo divide-se em três etapas:

    - Para cada professor e em cada dia, o código junta todas as aulas que ele dá e compara as horas de início e de fim.

    - Sempre que o professor tem uma aula mais cedo e outra mais tarde no mesmo dia (com tempos vagos no meio), é criado um alerta que só é ativado se ambas as aulas acontecerem mesmo.

    - O código conta quantas horas o professor fica a aguardar no meio dessas duas aulas e pede ao solver para minimizar esse total:

    $$
    \min \sum_{p, dia, s_1, s_2} \left( \text{Existe Buraco}_{p, dia, s_1, s_2} \times \text{Horas Vagas no Meio} \right)
    $$
    """)
    return


@app.cell
def _(DIAS, aulas, disciplinas, model):
    # O1. Minimizar o número total de "buracos" no horário de cada professor — um buraco é um tempo livre, no meio do dia, entre a primeira e a última aula desse professor nesse dia.

    penalizacoes_de_buracos = []

    lista_professores = disciplinas["professor"].unique()

    for professor_atual in lista_professores:
        for dia_da_semana in DIAS:

            aulas_do_professor_no_dia = []

            for (_turma, disciplina, _sala, dia_aula, slot_tempo), variavel_aula in aulas.items():

                professor_da_disciplina = disciplinas[disciplinas["disciplina"] == disciplina]["professor"].item()

                if professor_da_disciplina == professor_atual and dia_aula == dia_da_semana:
                    aulas_do_professor_no_dia.append((slot_tempo, variavel_aula))

            for slot_inicio, aula_inicio in aulas_do_professor_no_dia:
                for slot_fim, aula_fim in aulas_do_professor_no_dia:

                    if slot_fim > slot_inicio + 1:

                        tempo_vago_no_meio = slot_fim - slot_inicio - 1

                        existe_buraco = model.NewBoolVar(f"buraco_{professor_atual}_{dia_da_semana}_{slot_inicio}_{slot_fim}")
                        model.AddBoolAnd([aula_inicio, aula_fim]).OnlyEnforceIf(existe_buraco)

                        penalizacoes_de_buracos.append(existe_buraco * tempo_vago_no_meio)

    model.Minimize(sum(penalizacoes_de_buracos))
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Execução do Solver (CP-SAT)

    Após a definição de todas as variáveis, restrições e objetivos de otimização, o solver CP-SAT procura uma solução válida.

    O algoritmo busca encontrar um horário que satisfaça 100% das restrições obrigatórias e minimize as penalizações definidas.
    """)
    return


@app.cell
def _(cp_model, model):
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print("Status: Solução Encontrada!")
    else:
        print("Nenhuma solução válida foi encontrada.")
    return (solver,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    #  Testes de Validação do Horário

    Para ter a certeza de que o programa não cometeu erros, foram criados testes que analisam a solução final encontrada pelo solver.

    Estes testes usam a instrução assert para verificar se todas as regras da escola foram cumpridas.
    Se o código correr do início ao fim sem dar erros, significa que o horário está 100% correto e aprovado.
    """)
    return


@app.cell
def _(DIAS, SLOTS, aulas, disciplinas, salas, solver, turmas):
    # Teste R1 -- Uma turma não pode ter duas aulas em simultâneo.
    def test_r1():

        for i_r1, turma_r1 in turmas.iterrows():
            t_r1 = turma_r1["turma"]

            for dia in DIAS:
                for slot in SLOTS:


                    total_aulas = 0
                    for j_r1, disc in disciplinas.iterrows():
                        d_r1 = disc["disciplina"]
    
                        for k_r1, sala in salas.iterrows():
                            s_r1 = sala["sala"]

                            chave = (t_r1, d_r1, s_r1, dia, slot)


                            if chave in aulas and solver.Value(aulas[chave]) == 1:
                                total_aulas += 1

  
                    assert total_aulas <= 1

    return


@app.cell
def _(DIAS, SLOTS, aulas, disciplinas, salas, solver, turmas):
    # Teste R2 -- Cada disciplina cumpre exatamente a carga semanal definida em disciplinas.csv, para cada turma
    def test_r2():
        for j_r2, turma_r2 in turmas.iterrows():
            t_r2 = turma_r2["turma"]

            for i_r2, disc_r2 in disciplinas.iterrows():
                d_r2 = disc_r2["disciplina"]
                carga_exigida = disc_r2["carga_semanal"]
    
                total_aulas_semana = 0

                for k_r2, sala_r2 in salas.iterrows():
                    s_r2 = sala_r2["sala"]
                    for dia_r2 in DIAS:
                        for slot_r2 in SLOTS:
                            chave = (t_r2, d_r2, s_r2, dia_r2, slot_r2)

                            if chave in aulas and solver.Value(aulas[chave]) == 1:
                                total_aulas_semana += 1

                assert total_aulas_semana == carga_exigida

    return


@app.cell
def _(DIAS, SLOTS, aulas, disciplinas, salas, solver, turmas):
    # Teste R3 -- No máximo uma aula da mesma disciplina por dia, por turma — exceto disciplinas de duplo período (ver R4), em que o bloco de 2 tempos conta como uma só ocorrência nesse dia
    def test_r3():
        for j_r3 , turma_r3 in turmas.iterrows():
            t_r3 = turma_r3["turma"]

            for i_r3, disc_r3 in disciplinas.iterrows():
                d_r3 = disc_r3["disciplina"]
                s_duplo = str(disc_r3["duplo_periodo"]).strip().lower() == "sim"

                max_aulas = 2 if s_duplo else 1
                for dia_r3 in DIAS:
                    aulas_dadas = 0
                    for k_r3, sala_r3 in salas.iterrows():
                        s_r3 = sala_r3["sala"]
                        for slot_r3 in SLOTS:

                                chave = (t_r3, d_r3, s_r3, dia_r3, slot_r3)
                                if chave in aulas and solver.Value(aulas[chave]) == 1:
                                    aulas_dadas +=1
                    assert aulas_dadas <= max_aulas

    return


@app.cell
def _(DIAS, SLOTS, aulas, disciplinas, salas, solver, turmas):
    # Teste R4 -- Disciplinas marcadas duplo_periodo=sim só podem ser dadas em blocos de 2 tempos consecutivos, no mesmo dia (nunca um tempo isolado)
    def test_r4():
        for j_r4, turma_r4 in turmas.iterrows():
            t_r4 = turma_r4["turma"]

            for i_r4, disc_r4 in disciplinas.iterrows():
                d_r4 = disc_r4["disciplina"]
                duplo = str(disc_r4["duplo_periodo"]).strip().lower()

                for dia_r4 in DIAS:
                    slots_com_aula = []

                    for slot_r4 in SLOTS:
                        for k_r4, sala_r4 in salas.iterrows():
                            chave = (t_r4, d_r4, sala_r4["sala"], dia_r4, slot_r4)
                        
                            if chave in aulas and solver.Value(aulas[chave]) == 1:
                                slots_com_aula.append(slot_r4)
                                break

                    num_aulas_dia = len(slots_com_aula)

                    if duplo == "sim":
                        assert num_aulas_dia in [0, 2]

                        if num_aulas_dia == 2:
                            slot_1 = slots_com_aula[0]
                            slot_2 = slots_com_aula[1]
                            assert slot_2 == slot_1 + 1
                    else:
                        assert num_aulas_dia in [0, 1]

    return


@app.cell
def _(DIAS, SLOTS, aulas, disciplinas, salas, solver, turmas):
    # Teste R5 -- Um professor não pode dar duas aulas em simultâneo, mesmo que sejam a turmas ou disciplinas diferentes
    def test_r5():
        professores = disciplinas["professor"].dropna().unique()

        for prof_r5 in professores:
            disc_prof = disciplinas[disciplinas["professor"] == prof_r5]

            for dia_r5 in DIAS:
                for slot_r5 in SLOTS:
                    aulas_prof = 0

                    for i_r5, disc_r5 in disc_prof.iterrows():
                        d_r5 = disc_r5["disciplina"]

                        for l_r5, turma_r5 in turmas.iterrows():
                            t_r5 = turma_r5["turma"]

                            for p_r5, salas_r5 in salas.iterrows():
                                s_r5 = salas_r5["sala"]

                                chave = (t_r5, d_r5, s_r5, dia_r5, slot_r5)
                                if chave in aulas and solver.Value(aulas[chave]) == 1:
                                    aulas_prof += 1

                    assert aulas_prof <= 1
        

    return


@app.cell
def _(aulas, disciplinas, indisponibilidade, salas, solver, turmas):
    # Teste R6 -- Um professor só pode dar aulas nos tempos em que está disponível (disponibilidade_excecoes.csv)
    def test_r6():

        mapa_dias = {"Seg": 1, "Ter": 2, "Qua": 3, "Qui": 4, "Sex": 5}

        for j_r6, exc in indisponibilidade.iterrows():
            prof_exc = exc["professor"]

   
            dia_exc = mapa_dias[str(exc["dia"]).strip()]


            periodo_exc = int(exc["periodo"])

            disc_prof_r6 = disciplinas[disciplinas["professor"] == prof_exc]

            for k_r6, disc_r6 in disc_prof_r6.iterrows():
                d_r6 = disc_r6["disciplina"]

                for l_r6, turma_r6 in turmas.iterrows():
                    t_r6 = turma_r6["turma"]

                    for p_r6, salas_r6 in salas.iterrows():
                        s_r6 = salas_r6["sala"]

                        chave = (t_r6, d_r6, s_r6, dia_exc, periodo_exc)


                        if chave in aulas:
                            assert solver.Value(aulas[chave]) == 0

    return


@app.cell
def _(DIAS, SLOTS, aulas, disciplinas, pd, salas, solver, turmas):
    # Teste R7 -- Cada aula ocupa uma sala. Disciplinas com sala_especial só podem usar salas desse tipo; as restantes usam salas normal. Em nenhum tempo o número de aulas a decorrer num tipo de sala pode exceder a quantidade desse tipo definida em salas.csv
    def test_r7():
        for j_r7, disc_r7 in disciplinas.iterrows():
            d_r7 = disc_r7["disciplina"]

            sala_esp = str(disc_r7["sala_especial"]).strip() if pd.notna(disc_r7["sala_especial"]) else ""
            is_especial = len(sala_esp) > 0 and sala_esp.lower() != "nan"

            for k_7, sala_r7 in salas.iterrows():
                s_r7 = sala_r7["sala"]
                tipo_sala = str(sala_r7["tipo"]).strip().lower()

                nao_compativel = False
                if is_especial and s_r7 != sala_esp:
                    nao_compativel = True
                if not is_especial and tipo_sala != "normal":
                    nao_compativel = True

                if nao_compativel:
                    for y_r7, turma_r7 in turmas.iterrows():
                        t_r7 = turma_r7["turma"]
                        for dia_r7 in DIAS:
                            for slot_r7 in SLOTS:
                                chave_r7 = (t_r7, d_r7, s_r7, dia_r7, slot_r7)
                                if chave_r7 in aulas:
                                    assert solver.Value(aulas[chave_r7]) == 0

        for k_r7, sala_r7 in salas.iterrows():
            s_r7 = sala_r7["sala"]
            qtd_max = int(sala_r7["quantidade"])

            for dia_r7 in DIAS:
                for slot_r7 in SLOTS:
                    aulas_na_sala = 0
                    for y_r7, turma_r7 in turmas.iterrows():
                        t_r7 = turma_r7["turma"]
                        for j_r7, disc_r7 in disciplinas.iterrows():
                            d_r7 = disc_r7["disciplina"]
                            chave_r7 = (t_r7, d_r7, s_r7, dia_r7, slot_r7)
                            if chave_r7 in aulas and solver.Value(aulas[chave_r7]) == 1:
                                aulas_na_sala += 1
                    assert aulas_na_sala <= qtd_max

    return


@app.cell
def _(disciplinas, indisponibilidade, salas, turmas):
    # Teste R8 
    def test_r8():
        assert not turmas.empty
        assert not disciplinas.empty
        assert not salas.empty
        assert not indisponibilidade.empty

        assert "turma" in turmas.columns

        cols_disciplinas = {"disciplina", "professor", "carga_semanal", "duplo_periodo", "sala_especial"}
        assert cols_disciplinas.issubset(disciplinas.columns)

        cols_salas = {"sala", "tipo", "quantidade"}
        assert cols_salas.issubset(salas.columns)

        cols_excecoes = {"professor", "dia", "periodo"}
        assert cols_excecoes.issubset(indisponibilidade.columns)

    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Visualização do Horário

    Esta secção pega no resultado final do solver e transforma-o numa tabela fácil de consultar.

    Com os menus interativos, é possível:
    - Escolher o modo de vista (ver o horário por Turma ou por Professor).
    - Filtrar a informação (selecionar a turma ou professor desejado no menu de seleção).
    - Consultar a grelha (ver as aulas organizadas por dias da semana e tempos letivos, com indicação da disciplina, sala e professor).
    """)
    return


@app.cell
def _(aulas, disciplinas, pd, solver):
    def gerar_horario(aulas_dict, disciplinas_df, cp_solver):
        prof_por_disc = disciplinas_df.set_index("disciplina")["professor"].to_dict()

        registos = []
        for (t, d, s_val, dia_val, slot_val), var in aulas_dict.items():
            if cp_solver.Value(var) == 1:
                registos.append(
                    {
                        "turma": t,
                        "disciplina": d,
                        "professor": prof_por_disc.get(d, "N/A"),
                        "sala": s_val,
                        "dia": dia_val,
                        "periodo": slot_val,
                    }
                )
        return pd.DataFrame(registos)



    df_horario = gerar_horario(aulas, disciplinas, solver)
    return (df_horario,)


@app.cell
def _(df_horario):

    opcoes_turmas = sorted(df_horario["turma"].unique().tolist())
    opcoes_professores = sorted(df_horario["professor"].unique().tolist())

    seletor_modo = mo.ui.dropdown(
        options=["Turma", "Professor"], value="Turma", label="Ver por:"
    )

    seletor_turma = mo.ui.dropdown(
        options=opcoes_turmas, value=opcoes_turmas[0], label="Turma:"
    )

    seletor_prof = mo.ui.dropdown(
        options=opcoes_professores,
        value=opcoes_professores[0],
        label="Professor:",
    )


    mo.hstack([seletor_modo, seletor_turma, seletor_prof])
    return seletor_modo, seletor_prof, seletor_turma


@app.cell
def _(df_horario, seletor_modo, seletor_prof, seletor_turma):
    if seletor_modo.value == "Turma":
        df_f = df_horario[df_horario["turma"] == seletor_turma.value].copy()
        df_f["info"] = df_f.apply(
            lambda r: f"<b>{r['disciplina']}</b><br><small> {r['sala']}<br> {r['professor']}</small>",
            axis=1,
        )
        titulo = f"### Horário da Turma: `{seletor_turma.value}`"
    else:
        df_f = df_horario[df_horario["professor"] == seletor_prof.value].copy()
        df_f["info"] = df_f.apply(
            lambda r: f"<b>{r['disciplina']}</b><br><small> Turma {r['turma']}<br> {r['sala']}</small>",
            axis=1,
        )
        titulo = f"### Horário do Professor: `{seletor_prof.value}`"

    grelha = df_f.pivot(index="periodo", columns="dia", values="info").fillna("-")

    dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]
    ordem_dias = [d for d in dias_semana if d in grelha.columns]

    if ordem_dias:
        grelha = grelha.reindex(columns=ordem_dias)

    mo.md(f""" {titulo} {grelha.to_html(escape=False, classes='table table-bordered table-hover')}""")
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Utilização de Ferramentas LLM

    O modelo de linguagem foi utilizado no esclarecimento de dúvidas,e no desenvolvimento da interface visual em Marimo.

    * Histórico de Diálogo: [Aceder ao Diálogo LLM](https://claude.ai/share/bb4fa134-8e12-4b37-ba92-3bc664ed204a)
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    #Trabalho realizado por:

    Fábio Miguel Costa Reis A109746

    Wu Hou Pan A109381
    """)
    return


if __name__ == "__main__":
    app.run()
