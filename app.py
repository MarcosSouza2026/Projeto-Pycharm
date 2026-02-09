import dash
from dash import dcc, html, Input, Output, State, ALL, callback_context
import pandas as pd
import dash_bootstrap_components as dbc
import json
import os
import base64
import flask
from flask import send_from_directory
import dash_quill
from datetime import datetime, date
import dash_auth

# ... (seus imports)

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG, dbc.icons.BOOTSTRAP],
    suppress_callback_exceptions=True
)

# 👈 O SERVER PRECISA ESTAR AQUI PARA O RENDER FUNCIONAR
server = app.server

# 1. Defina seus usuários e senhas
USUARIOS_SENHAS = {
    "Marcos": "h3g2z0b5",
    "Pedro": "fearhunger2",
    "Paulo": "Max506070",
    "Moises": "Max506070"
}

# 2. Ative a proteção (AGORA O APP JÁ EXISTE)
auth = dash_auth.BasicAuth(
    app,
    USUARIOS_SENHAS
)

# --- 1. CONFIGURAÇÕES E DADOS ---
CSV_FILE = 'instalacoes.csv'
CSV_AGENDA = 'agenda_tecnicos.csv'
CSV_KITS = 'kits_estoque.csv'
NOTAS_FILE = 'notas_base.json'
FOLDER_FILES = 'arquivos_base'

if not os.path.exists(CSV_AGENDA):
    pd.DataFrame(columns=[
        'id',                # 👈 ESSENCIAL
        'id_instalacao',
        'tecnico',
        'descricao',
        'status',
        'telefone',
        'observacoes',
        'data_inicio',
        'mes_referencia'
    ]).to_csv(CSV_AGENDA, index=False, sep=',', encoding='latin-1')


if not os.path.exists(FOLDER_FILES):
    os.makedirs(FOLDER_FILES)

COLUNAS = [
    'id_instalacao', 'tecnico', 'descricao', 'data_inicio', 'status',
    'materiais_checklist', 'mes_referencia',
    'responsavel', 'telefone', 'observacoes',
    'solucao',            # 👈 NOVO
    'valor_acordado'
]


LISTA_TECNICOS = ['Giovanni', 'Roberto', 'Pedro', 'Jobert', 'Leonardo', 'Gustavo', 'Valdeci', 'Farley']

MESES_PT = {
    "January": "Janeiro", "February": "Fevereiro", "March": "Março", "April": "Abril",
    "May": "Maio", "June": "Junho", "July": "Julho", "August": "Agosto",
    "September": "Setembro", "October": "Outubro", "November": "Novembro", "December": "Dezembro"
}


def init_csv():
    if not os.path.exists(CSV_FILE):
        pd.DataFrame(columns=COLUNAS).to_csv(CSV_FILE, index=False, sep=',', encoding='latin-1')
    else:
        df = pd.read_csv(CSV_FILE, sep=',', encoding='latin-1')
        if 'valor_acordado' not in df.columns:
            df['valor_acordado'] = ""
            df.to_csv(CSV_FILE, index=False, sep=',', encoding='latin-1')

    if not os.path.exists(CSV_KITS):
        pd.DataFrame(columns=['tecnico', 'item', 'qtd_tem', 'qtd_faltante']).to_csv(CSV_KITS, index=False, sep=',',
                                                                                    encoding='latin-1')


def load_data():
    if not os.path.exists(CSV_FILE): return pd.DataFrame(columns=COLUNAS)
    try:
        df = pd.read_csv(CSV_FILE, sep=',', encoding='latin-1', dtype={'id_instalacao': str})
        for col in COLUNAS:
            if col not in df.columns: df[col] = ""
        return df.fillna("")
    except:
        return pd.DataFrame(columns=COLUNAS)


init_csv()

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP],
    suppress_callback_exceptions=True, # ISSO DIZ PARA O DASH NÃO TRAVAR
)
server = app.server  # 👈 ESSA LINHA É OBRIGATÓRIA

@app.server.route('/download/<path:filename>')
def download_file(filename):
    return send_from_directory(FOLDER_FILES, filename, as_attachment=False)


def salvar_nota_json(conteudo):
    with open(NOTAS_FILE, 'w', encoding='utf-8') as f:
        json.dump({'conteudo': conteudo}, f)


def carregar_nota_json():
    if not os.path.exists(NOTAS_FILE):
        return ""
    try:
        with open(NOTAS_FILE, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()
            if not conteudo:  # Se o arquivo estiver vazio
                return ""
            data = json.loads(conteudo)
            return data.get('conteudo', '')
    except (json.JSONDecodeError, Exception):
        # Se der erro na leitura, retorna vazio em vez de travar o app
        return ""


def gerar_lista_arquivos(lista):
    return html.Ul([
        html.Li(
            html.Button(f, id={'type': 'btn-ver-arquivo', 'filename': f},
                        className="btn btn-link btn-sm text-info p-0 text-start",
                        style={'textDecoration': 'none', 'fontSize': '12px'}),
            className="mb-1"
        ) for f in lista
    ], style={'listStyle': 'none', 'padding': '0'})


# --- NAVBAR ---
navbar = dbc.Navbar(
    dbc.Container([
        html.A(dbc.Row([
            dbc.Col(html.Img(src="/assets/logo.png", height="45px"), width="auto"),
            dbc.Col(dbc.NavbarBrand("LOGÍSTICA MAXVEL", className="ms-3 fw-bold text-info"), width="auto"),
        ], align="center", className="g-0"), href="/", style={"textDecoration": "none"}),

        dbc.Row([
            dbc.Col([
                dbc.InputGroup([
                    dbc.InputGroupText(html.I(className="bi bi-search")),
                    dbc.Input(id="search-input", placeholder="O.S + Enter...", type="text", style={"width": "200px"},
                              debounce=True),
                ], size="sm")
            ])
        ], className="ms-auto me-3 d-none d-md-flex"),

        dbc.Nav([
            dbc.NavItem(
                dbc.Button([html.I(className="bi bi-plus-lg me-2"), "Nova O.S"], id='btn-novo', color="info", size="sm",
                           className="fw-bold")),
            dbc.NavItem(dcc.Dropdown(id='filtro-mes', style={'color': '#000', 'width': '180px'}, clearable=False,
                                     className="ms-3")),
        ], navbar=True)
    ], fluid=True),
    # AQUI ESTÁ O SEGREDO: Cor sólida para diferenciar do fundo e borda info
    color="#2c3e50",
    dark=True,
    className="mb-0 shadow-sm border-bottom border-info py-2 sticky-top"
)

# --- MODAIS ---
modal_principal = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Gerenciar Ordem de Serviço")),
    dbc.ModalBody([
        dcc.Store(id='modal-id-store'),
        dcc.Store(id="modo-modal-os", data="OS"),
        dcc.Store(id='temp-items-store', data=[]),
        dcc.Store(id='store-index-item-deletar'),
        dbc.Row([
            dbc.Col([dbc.Label("Número da O.S:"), dbc.Input(id='modal-id-manual', type='text')], width=4),
            dbc.Col([dbc.Label("Descrição:"), dbc.Input(id='modal-desc', type='text')], width=8),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([dbc.Label("Responsável:"), dbc.Input(id='modal-resp', type='text')], width=5),
            dbc.Col([dbc.Label("Telefone:"), dbc.Input(id='modal-tel', type='text')], width=4),
            dbc.Col([dbc.Label("Valor Acordado:"), dbc.Input(id='modal-valor', type='text', placeholder="R$ 0,00")],
                    width=3),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([dbc.Label("Técnico:"),
                     dcc.Dropdown(id='modal-tec', options=[{'label': t, 'value': t} for t in LISTA_TECNICOS],
                                  style={'color': '#000'})], width=6),
            dbc.Col([dbc.Label("Status:"), dbc.Select(id='modal-status', options=[
                {"label": "Aberto", "value": "Aberto"}, {"label": "Em Andamento", "value": "Em Andamento"},
                {"label": "Finalizada", "value": "Finalizada"}
            ])], width=3),
            dbc.Col([dbc.Label("Data/Hora:"), dbc.Input(id='modal-data', type='datetime-local')], width=3),
        ], className="mb-3"),
        dbc.Label("Observações:"),
        dbc.Textarea(id='modal-obs', style={"height": "70px"}, className="mb-3"),
        html.Hr(),
        html.H6("Materiais", className="text-info"),
        dbc.Row([
            dbc.Col(dbc.Input(id='input-lista', placeholder="Item..."), width=6),
            dbc.Col(dbc.Input(id='input-qtd', type='number', value=1), width=2),
            dbc.Col(dbc.Button("Add", id="btn-gerar", color="info", outline=True), width=3),
            dbc.Col(dbc.Button(html.I(className="bi bi-trash"), id="btn-abrir-clear", color="link",
                               className="text-warning p-0"), width=1),
        ], className="g-2 mb-3 align-items-end"),
        html.Div(id='lista-materiais-container', style={"maxHeight": "200px", "overflowY": "auto"})
    ]),
    dbc.ModalFooter([
        dbc.Button("Excluir", id="btn-excluir-os", n_clicks=0, color="danger", size="sm", outline=True,
                   className="me-auto"),
        dbc.Button("Fechar", id="btn-fechar-os", n_clicks=0, color="secondary", size="sm"),
        dbc.Button("Salvar", id="btn-salvar-os", n_clicks=0, color="success", size="sm", className="px-4"),
    ]),
], id="main-modal", is_open=False, size="lg")

modal_agenda = dbc.Modal([
    dbc.ModalHeader(
        dbc.ModalTitle("Novo Agendamento de Manutenção"),
        id="agenda-modal-header"
    ),
    dbc.ModalBody([
        dcc.Store(id='agenda-id-store'),

        dbc.Row([
            dbc.Col([dbc.Label("Nº O.S:"), dbc.Input(id='agenda-id-manual', type='text')], width=4),
            dbc.Col([dbc.Label("Cliente:"), dbc.Input(id='agenda-cliente', type='text')], width=8),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([dbc.Label("Telefone:"), dbc.Input(id='agenda-tel', type='text')], width=6),
            dbc.Col([dbc.Label("Técnico:"),
                     dcc.Dropdown(id='agenda-tec', options=[{'label': t, 'value': t} for t in LISTA_TECNICOS],
                                  style={'color': '#000'})], width=6),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Status:"),
                dbc.Select(
                    id='agenda-status',
                    options=[
                        {"label": "Aberta", "value": "Aberta"},
                        {"label": "Pendente", "value": "Pendente"},
                        {"label": "Finalizada", "value": "Finalizada"}
                    ],
                    value=None,  # 👈 ESSENCIAL
                    placeholder="Selecione o status"
                )
            ], width=6),

            dbc.Col([
                dbc.Label("Data/Hora:"),
                dbc.Input(id='agenda-data', type='datetime-local')
            ], width=6),
        ], className="mb-3"),

        dbc.Label("Problema Reclamado:"),
        dbc.Textarea(
            id='agenda-obs',
            style={"height": "100px"},
            className="mb-3"
        ),

        dbc.Label(
            "SOLUÇÃO / MOTIVO DA PENDÊNCIA:",
            style={
                "color": "#ffc107",
                "fontWeight": "bold"
            }
        ),

        dbc.Textarea(
            id='agenda-info-final',
            style={"height": "100px"},
            placeholder="Descreva a solução aplicada ou o motivo da pendência...",
            className="mb-3"
        ),
    ]),

    dbc.ModalFooter([
        dbc.Button(
            "Excluir",
            id="agenda-btn-excluir",
            color="danger",
            className="me-auto"
        ),
        dbc.Button("Fechar", id="agenda-btn-fechar", className="me-2"),
        dbc.Button("Salvar Manutenção", id="agenda-btn-salvar", color="success")
    ]),
],
    id="modal-agenda",
    is_open=False,
    size="lg",
    style={"backgroundColor": "#121212"},
    content_style={"backgroundColor": "#1e1e1e", "color": "white"}
)

modal_pergunta_finalizar = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Finalizar O.S")),
    dbc.ModalBody([dbc.Textarea(id='input-obs-final', placeholder="Observação de fechamento...")]),
    dbc.ModalFooter([dbc.Button("Voltar", id="btn-cancel-final-obs"),
                     dbc.Button("Salvar e Finalizar", id="btn-confirm-final-obs", color="success")]),
], id="modal-pergunta-finalizar", is_open=False, centered=True)

confirm_modal_inst = dbc.Modal([
    dbc.ModalHeader("Excluir Registro?"),
    dbc.ModalFooter(
        [dbc.Button("Sim", id="btn-excluir-confirmado", color="danger"), dbc.Button("Não", id="btn-excluir-cancelar")]),
], id="confirm-modal", is_open=False, centered=True)

confirm_clear_all = dbc.Modal([
    dbc.ModalHeader("Limpar materiais?"),
    dbc.ModalFooter([dbc.Button("Sim", id="btn-clear-sim", color="danger"), dbc.Button("Não", id="btn-clear-nao")]),
], id="modal-conf-clear", is_open=False, centered=True)

modal_conf_item_unico = dbc.Modal([
    dbc.ModalHeader("Remover item?"),
    dbc.ModalFooter([dbc.Button("Remover", id="btn-confirm-del-item", color="danger"),
                     dbc.Button("Cancelar", id="btn-cancel-del-item")]),
], id="modal-item-unico", is_open=False, centered=True)

# --- LAYOUT PRINCIPAL ---
app.layout = html.Div([
    html.Div(style={'position': 'fixed', 'top': '50%', 'left': '50%', 'transform': 'translate(-50%, -50%)',
                    'backgroundImage': 'url("/assets/logo.png")', 'backgroundRepeat': 'no-repeat',
                    'backgroundPosition': 'center', 'backgroundSize': 'contain', 'width': '60vw', 'height': '60vh',
                    'opacity': '0.04', 'zIndex': '0', 'pointerEvents': 'none'}),

    navbar,
    dbc.Container([
        dbc.Tabs([
            dbc.Tab(label="Gestão de O.S.", tab_id="tab-os", label_class_name="fw-bold text-info"),
            dbc.Tab(label="Kit de Manutenção", tab_id="tab-kit", label_class_name="fw-bold text-info"),
            dbc.Tab(label="Base de Conhecimento", tab_id="tab-base", label_class_name="fw-bold text-info"),
            dbc.Tab(label="Agenda Técnicos", tab_id="tab-agenda", label_class_name="fw-bold text-info"),

        ], id="tabs-principal", active_tab="tab-os", className="mt-3 mb-4"),

        html.Div(id="conteudo-aba"),

        dcc.Store(id='refresh-signal', data=0),
        dcc.Store(id='refresh-kit-signal', data=0),

        modal_principal,
        modal_pergunta_finalizar,
        confirm_modal_inst,
        confirm_clear_all,
        modal_conf_item_unico,
        modal_agenda,

        # 🛡️ PROTEÇÃO: Botões invisíveis para o Dash não reclamar nas outras abas
        html.Button(id="btn-nova-agenda", style={"display": "none"}),


    ], fluid=True, style={'position': 'relative', 'zIndex': '1'})  # Fechamento do Container
], style={"backgroundColor": "#121212", "minHeight": "100vh"})  # Fechamento do layout


# --- RENDERIZAÇÃO ABAS ---
def render_aba_os():
    return dbc.Container([dcc.Loading(
        html.Div(id='cards-area', className='row row-cols-1 row-cols-md-2 row-cols-lg-3 row-cols-xl-4 g-4'), type="dot",
        color="#0dcaf0")], fluid=True)


def render_aba_kit():
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Checklist Kit Permanente (Ferramentas)", className="mb-0 text-info")),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([dbc.Label("Técnico:"), dcc.Dropdown(id='dropdown-kit-tec',
                                                                         options=[{'label': t, 'value': t} for t in
                                                                                  LISTA_TECNICOS],
                                                                         placeholder="Selecione...",
                                                                         style={'color': '#000'})], width=4),
                            dbc.Col(id="resumo-kit-col", width=5),
                            dbc.Col(
                                [dbc.Button([html.I(className="bi bi-save me-2"), "Salvar Kit"], id="btn-salvar-kit",
                                            color="success", className="mt-4")], width=3, className="text-end")
                        ], className="mb-4 align-items-end"),
                        html.Div(id='tabela-kit-container')
                    ])
                ], color="dark", outline=True, className="border-info shadow")
            ], width=12)
        ])
    ], className="p-2")


def render_aba_base():
    conteudo_salvo = carregar_nota_json()
    arquivos_lista = os.listdir(FOLDER_FILES)
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Documentação e Senhas", className="text-info mb-0")),
                    dbc.CardBody([
                        html.Div([dash_quill.Quill(id='editor-texto', value=conteudo_salvo, modules={
                            'toolbar': [['bold', 'italic', 'underline'], [{'list': 'ordered'}, {'list': 'bullet'}],
                                        ['link']]})],
                                 style={'height': '350px', 'backgroundColor': 'white', 'color': 'black',
                                        'marginBottom': '50px'}),
                        dbc.Button("Salvar Documentação", id="btn-salvar-base", color="success", className="mt-3")
                    ])
                ], color="dark", outline=True, className="border-info")
            ], width=5),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Anexos e Visualizador", className="text-info mb-0")),
                    dbc.CardBody([
                        dcc.Upload(id='upload-base', children=html.Div(['Arraste ou ', html.A('Selecione')]),
                                   style={'width': '100%', 'height': '40px', 'lineHeight': '40px', 'borderWidth': '1px',
                                          'borderStyle': 'dashed', 'borderRadius': '5px', 'textAlign': 'center',
                                          'marginBottom': '10px'}, multiple=True),
                        dbc.Row([
                            dbc.Col([html.H6("Arquivos:", className="small text-muted"),
                                     html.Div(id='lista-arquivos-base', children=gerar_lista_arquivos(arquivos_lista),
                                              style={'maxHeight': '400px', 'overflowY': 'auto'})], width=4),
                            dbc.Col([html.H6("Visualização:", className="small text-muted"),
                                     html.Iframe(id='visualizador-frame',
                                                 style={'width': '100%', 'height': '400px', 'border': '1px solid #444',
                                                        'backgroundColor': '#fff'})], width=8)
                        ])
                    ])
                ], color="dark", outline=True, className="border-info")
            ], width=7)
        ])
    ], className="p-3")


# --- CALLBACKS GERAIS ---
@app.callback(Output("conteudo-aba", "children"), Input("tabs-principal", "active_tab"))
def alternar_abas(tab_ativa):
    if tab_ativa == "tab-kit": return render_aba_kit()
    if tab_ativa == "tab-base": return render_aba_base()

    if tab_ativa == "tab-agenda":
        return html.Div([

            # 1. Tabs de cidades
            dbc.Tabs([
                dbc.Tab(label="DIVINÓPOLIS", tab_id="ag-div"),
                dbc.Tab(label="ITAÚNA", tab_id="ag-ita"),
            ], id="tabs-agenda-cidades", active_tab="ag-div", className="mb-3"),

            # 2. Botão Nova Manutenção
            dbc.Row([
                dbc.Col(
                    dbc.Button(
                        [html.I(className="bi bi-plus-circle me-2"), "Nova Manutenção"],
                        id="btn-trigger-agenda",
                        color="success"
                    ),
                    width="auto"
                )
            ], justify="end", className="mb-2 px-3"),

            # 📅 3. CALENDÁRIO (AQUI É O LUGAR CERTO)
            dbc.Row([
                dbc.Col(
                    dcc.DatePickerSingle(
                        id="agenda-data-selecionada",
                        date=date.today(),
                        display_format="DD/MM/YYYY",
                        className="mb-3"
                    ),
                    width="auto"
                )
            ], className="px-3"),

            # 4. Área dos cards
            html.Div([
                dcc.Loading(
                    html.Div(id="cards-agenda-area", className="w-100"),
                    type="dot"
                )
            ], style={
                "width": "100vw",
                "marginLeft": "calc(-50vw + 50%)",
                "marginRight": "calc(-50vw + 50%)",
                "padding": "0 20px"
            })
        ])

    return render_aba_os()



# --- CALLBACKS KIT ---
@app.callback(Output('tabela-kit-container', 'children'),
              [Input('dropdown-kit-tec', 'value'), Input('refresh-kit-signal', 'data')])
def carregar_tabela_kit(tecnico, sig):
    if not tecnico: return html.Div("Selecione um técnico.", className="text-muted text-center py-5")
    itens = ["BATERIA 7A", "BATERIA SENSOR 8000", "BATERIA SENSOR 8000 JANELA", "CABO BIPOLAR", "CABO DE 6 VIAS",
             "CÂMERA 2 MP ANALÓGICA", "CONECTOR BNC", "CONECTOR P4", "MÓDULO GPRS INTELBRAS 8000", "MÓDULO ETHERNET",
             "MÓDULO GPRS 3G JFL", "SENSOR 8000 JANELA", "SENSOR 8000 INTERNO", "SENSOR DSE 830", "SENSOR IDX 1001",
             "SENSOR SEMI ABERTO IRD 640 JFL", "FONTE 10A", "SIRENE"]
    df_kits = pd.read_csv(CSV_KITS, sep=',', encoding='latin-1')
    dados_tec = df_kits[df_kits['tecnico'] == tecnico]
    rows = []
    for i, item in enumerate(itens):
        ext = dados_tec[dados_tec['item'] == item]
        q_t, q_f = (ext.iloc[0]['qtd_tem'], ext.iloc[0]['qtd_faltante']) if not ext.empty else (0, 0)
        sw = [1] if q_f == 0 and q_t > 0 else []
        rows.append(html.Tr([
            html.Td(dbc.Checklist(options=[{"label": "", "value": 1}], value=sw, id={'type': 'kit-switch', 'index': i},
                                  switch=True)),
            html.Td(html.Span(item, id={'type': 'kit-item-nome', 'index': i}), className="fw-bold"),
            html.Td(dbc.Input(type="number", value=q_t, id={'type': 'kit-qtd-tem', 'index': i}, size="sm",
                              style={"width": "80px", "backgroundColor": "#2b2b2b", "color": "white"})),
            html.Td(dbc.Input(type="number", value=q_f, id={'type': 'kit-qtd-falta', 'index': i}, size="sm",
                              style={"width": "80px", "backgroundColor": "#2b2b2b", "color": "#ff4d4d"})),
        ]))
    return dbc.Table(
        [html.Thead(html.Tr([html.Th("Status"), html.Th("Nome do Item"), html.Th("Qtd. Atual"), html.Th("Faltante")]),
                    className="table-secondary"), html.Tbody(rows)], bordered=True, hover=True, color="dark",
        striped=True)


@app.callback([Output('btn-salvar-kit', 'children'), Output('refresh-kit-signal', 'data')],
              Input('btn-salvar-kit', 'n_clicks'),
              [State('dropdown-kit-tec', 'value'), State({'type': 'kit-item-nome', 'index': ALL}, 'children'),
               State({'type': 'kit-qtd-tem', 'index': ALL}, 'value'),
               State({'type': 'kit-qtd-falta', 'index': ALL}, 'value'), State('refresh-kit-signal', 'data')],
              prevent_initial_call=True)
def salvar_dados_kit(n, tec, nomes, qs_t, qs_f, sig):
    if not tec: return dash.no_update
    df = pd.read_csv(CSV_KITS, sep=',', encoding='latin-1')
    df = df[df['tecnico'] != tec]
    novos = [{'tecnico': tec, 'item': n, 'qtd_tem': t if t else 0, 'qtd_faltante': f if f else 0} for n, t, f in
             zip(nomes, qs_t, qs_f)]
    pd.concat([df, pd.DataFrame(novos)]).to_csv(CSV_KITS, index=False, sep=',', encoding='latin-1')
    return [html.I(className="bi bi-check-circle me-2"), "Kit Salvo!"], (sig or 0) + 1


# --- CALLBACKS GESTÃO O.S. (TRAVA DEFINITIVA DE MODAIS) ---
@app.callback(
    [Output("confirm-modal", "is_open"),
     Output("modal-conf-clear", "is_open"),
     Output("modal-item-unico", "is_open"),
     Output("modal-pergunta-finalizar", "is_open"),
     Output("store-index-item-deletar", "data")],
    [Input("btn-abrir-confirm", "n_clicks"),
     Input("btn-abrir-clear", "n_clicks"),
     Input({"type": "btn-del-single", "index": ALL}, "n_clicks"),
     Input("btn-salvar", "n_clicks"),
     Input("btn-excluir-confirmado", "n_clicks"),
     Input("btn-clear-sim", "n_clicks"),
     Input("btn-confirm-del-item", "n_clicks"),
     Input("btn-confirm-final-obs", "n_clicks"),
     Input("btn-excluir-cancelar", "n_clicks"),
     Input("btn-clear-nao", "n_clicks"),
     Input("btn-cancel-del-item", "n_clicks"),
     Input("btn-cancel-final-obs", "n_clicks")],
    [State("modal-status", "value")],
    prevent_initial_call=True
)
def toggle_all_confirms(n_conf, n_clear, n_single, n_save, n_ex_c, n_cl_s, n_it_c, n_fi_c, n_ex_n, n_cl_n, n_it_n,
                        n_fi_n, status_atual):
    ctx = callback_context
    if not ctx.triggered:
        return False, False, False, False, dash.no_update

    trig_id = ctx.triggered[0]['prop_id']

    # abrir confirmações
    if "btn-abrir-confirm.n_clicks" in trig_id and n_conf: return True, False, False, False, dash.no_update
    if "btn-abrir-clear.n_clicks" in trig_id and n_clear: return False, True, False, False, dash.no_update

    # excluir item único
    if "btn-del-single" in trig_id and n_single:
        val = ctx.triggered[0]['value']
        if val:
            idx = json.loads(trig_id.split('.')[0])['index']
            return False, False, True, False, idx

    # salvar OS
    if "btn-salvar.n_clicks" in trig_id and n_save:
        return False, False, False, True, dash.no_update

    # fechar modal OS
    if "btn-fechar.n_clicks" in trig_id and n_cl_s:
        return False, False, False, False, dash.no_update

    # excluir OS
    if "btn-excluir.n_clicks" in trig_id and n_ex_c:
        return False, False, True, False, dash.no_update

    return False, False, False, False, None



@app.callback(
    [Output("main-modal", "is_open"),
     Output('modal-id-store', 'data'),
     Output('modal-id-manual', 'value'),
     Output('modal-desc', 'value'),
     Output('modal-tec', 'value'),
     Output('modal-data', 'value'),
     Output('temp-items-store', 'data', allow_duplicate=True),
     Output('modal-status', 'value'),
     Output('modal-resp', 'value'),
     Output('modal-tel', 'value'),
     Output('modal-obs', 'value'),
     Output('modal-valor', 'value'),
     Output('input-obs-final', 'value')],
    [Input('btn-novo', 'n_clicks'),
     Input({'type': 'edit', 'index': ALL}, 'n_clicks'),
     Input('btn-salvar-os', 'n_clicks'),
     Input('btn-confirm-final-obs', 'n_clicks'),
     Input('btn-fechar-os', 'n_clicks'),
     Input('btn-excluir-os', 'n_clicks')],
    [State('modal-status', 'value')],
    prevent_initial_call=True
)
def manage_main(n_novo, n_edit, n_s, n_confirm_f, n_f, n_ex, status_atual):
    ctx = callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate


    trig_id = ctx.triggered[0]['prop_id']
    trig_val = ctx.triggered[0]['value']

    # 1. Lógica para Editar / Criar O.S.
    if "edit" in trig_id:
        if not trig_val:
            raise dash.exceptions.PreventUpdate
        try:
            clean_id = trig_id.split('.n_clicks')[0]
            tid_dict = json.loads(clean_id)
            tid = str(tid_dict['index'])

            df = load_data()
            row_filter = df[df['id_instalacao'].astype(str) == tid]

            # 🔥 AQUI ESTÁ A CORREÇÃO (VERSÃO 1)
            if row_filter.empty:
                print(f"O.S. {tid} não encontrada. Criando nova O.S...")

                nova_os = {
                    'id_instalacao': tid,
                    'descricao': '',
                    'tecnico': '',
                    'data_inicio': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'status': 'Pendente',
                    'responsavel': '',
                    'telefone': '',
                    'observacoes': '',
                    'materiais_checklist': '',
                    'valor_acordado': ''
                }

                df = pd.concat([df, pd.DataFrame([nova_os])], ignore_index=True)
                df.to_csv(CSV_FILE, index=False, encoding='latin-1')

                row = nova_os
                itms = []
                val_os = ""

            else:
                row = row_filter.iloc[0]

                itms = []
                if row['materiais_checklist']:
                    for i in str(row['materiais_checklist']).split(';'):
                        if '|' in i:
                            p = i.split('|')
                            itms.append({
                                'label': p[0],
                                'total': float(p[1]),
                                'entregue': float(p[2])
                            })

                val_os = row.get('valor_acordado', "")

            return (
                True,
                tid,
                row['id_instalacao'],
                row['descricao'],
                row['tecnico'],
                str(row['data_inicio']).replace(' ', 'T'),
                itms,
                row['status'],
                row.get('responsavel', ''),
                row.get('telefone', ''),
                row.get('observacoes', ''),
                val_os,
                ""
            )

        except Exception as e:
            print(f"Erro ao interpretar ID de edição: {e}")
            return [dash.no_update] * 13


    # 2. Lógica para Nova O.S.
    if "btn-novo" in trig_id:
        return True, str(datetime.now().timestamp()), "", "", None, \
            datetime.now().strftime("%Y-%m-%dT%H:%M"), [], "Aberto", \
            "", "", "", "", ""

    # 3. Lógica para Fechar/Excluir/Finalizar (Fecha o modal e limpa)
    if any(x in trig_id for x in ["btn-fechar", "btn-excluir-confirmado", "btn-confirm-final-obs"]):
        return False, dash.no_update, "", "", None, "", [], "Aberto", "", "", "", "", ""

    # 4. Lógica para Salvar (se não for finalizada, fecha o modal)
    if "btn-salvar" in trig_id:
        if status_atual != "Finalizada":
            return False, dash.no_update, "", "", None, "", [], "Aberto", "", "", "", "", ""
        else:
            return [dash.no_update] * 13

    return [dash.no_update] * 13


# --- MATERIAIS, CARDS E SALVAMENTO ---
@app.callback(
    [Output('temp-items-store', 'data'),
     Output('input-lista', 'value')],
    [Input('btn-gerar', 'n_clicks'),
     Input('btn-clear-sim', 'n_clicks'),
     Input('btn-confirm-del-item', 'n_clicks'),
     Input({'type': 'qtd-total', 'index': ALL}, 'value'),
     Input({'type': 'qtd-entregue', 'index': ALL}, 'value')],
    [State('input-lista', 'value'),
     State('input-qtd', 'value'),
     State('temp-items-store', 'data'),
     State('store-index-item-deletar', 'data')],
    prevent_initial_call=True
)
def update_items(n_add, n_clr, n_del, totals, entregues, txt, q_add, current, idx_del):
    ctx = callback_context
    trig_id = ctx.triggered[0]['prop_id']
    if current:
        for i in range(min(len(current), len(totals))):
            try:
                current[i]['total'] = float(totals[i]) if totals[i] is not None else 0
                current[i]['entregue'] = float(entregues[i]) if entregues[i] is not None else 0
            except:
                pass
    if "btn-gerar" in trig_id and txt:
        current.append({'label': txt, 'total': float(q_add or 1), 'entregue': 0})
        return current, ""
    if "btn-clear-sim" in trig_id: return [], ""
    if "btn-confirm-del-item" in trig_id and idx_del is not None:
        if 0 <= idx_del < len(current): current.pop(idx_del)
        return current, dash.no_update
    return current, dash.no_update


@app.callback(Output('lista-materiais-container', 'children'), Input('temp-items-store', 'data'))
def render_list(items):
    if not items: return html.Div("Nenhum material.", className="text-muted small text-center py-2")
    rows = [dbc.Row([dbc.Col(html.Small("Item"), width=6), dbc.Col(html.Small("Total"), width=2),
                     dbc.Col(html.Small("Uso"), width=2), dbc.Col(width=2)], className="mb-2 text-info fw-bold")]
    for i, it in enumerate(items):
        cor = "#2eb82e" if it['entregue'] >= it['total'] and it['total'] > 0 else "#ffc107"
        rows.append(dbc.Row([
            dbc.Col(html.Span(it['label'], className="small"), width=6),
            dbc.Col(dbc.Input(id={'type': 'qtd-total', 'index': i}, type='number', value=it['total'], size="sm"),
                    width=2),
            dbc.Col(dbc.Input(id={'type': 'qtd-entregue', 'index': i}, type='number', value=it['entregue'], size="sm",
                              style={"color": cor}), width=2),
            dbc.Col(
                dbc.Button(html.I(className="bi bi-x-circle"), id={'type': 'btn-del-single', 'index': i}, color="link",
                           className="text-danger p-0"), width=2)
        ], className="mb-2 align-items-center"))
    return rows


@app.callback(
    Output('refresh-signal', 'data'),
    [Input('btn-salvar', 'n_clicks'),
     Input('btn-confirm-final-obs', 'n_clicks'),
     Input('btn-excluir-confirmado', 'n_clicks')],
    [State('modal-id-store', 'data'),
     State('modal-id-manual', 'value'),
     State('modal-desc', 'value'),
     State('modal-tec', 'value'),
     State('modal-data', 'value'),
     State('temp-items-store', 'data'),
     State('modal-status', 'value'),
     State('modal-resp', 'value'),
     State('modal-tel', 'value'),
     State('modal-obs', 'value'),
     State('modal-valor', 'value'),
     State('input-obs-final', 'value'),
     State('modal-solucao', 'value'),
     State('refresh-signal', 'data')],
    prevent_initial_call=True
)
def save_data(
        n1, n2, n3,
        mid_s, mid_m, desc, tec, dt, itms,
        stat, resp, tel, obs_v, valor, obs_n,
        solucao,
        sig
):
    ctx = callback_context
    trig_id = ctx.triggered[0]['prop_id']

    if "btn-salvar" in trig_id and stat == "Finalizada":
        return dash.no_update

    df = load_data()

    # Garantir que a coluna id_instalacao seja tratada como string para comparação
    df['id_instalacao'] = df['id_instalacao'].astype(str)

    if "btn-excluir-confirmado" in trig_id:
        df = df[df['id_instalacao'] != str(mid_s)]
    else:
        obs_f = obs_v
        if obs_n:
            obs_f = f"{obs_v}\n[{datetime.now().strftime('%d/%m')}] {obs_n}".strip()

        txt = ";".join([f"{i['label']}|{i['total']}|{i['entregue']}" for i in itms])
        dt_f = dt.replace('T', ' ') if dt else ""
        mes = f"{MESES_PT.get(datetime.now().strftime('%B'))}/{datetime.now().year}"

        # 1. BUSCA A LINHA: Usamos mid_s (ID que veio do Gerenciar) para achar a OS
        mask = df['id_instalacao'] == str(mid_s)

        if not df[mask].empty:
            # 2. SE ACHOU, ATUALIZA (Inclusive o Status)
            idx = df.index[mask][0]
            # Se mid_m tiver valor, atualiza o ID, senão mantém o mid_s
            df.at[idx, 'id_instalacao'] = str(mid_m) if mid_m else str(mid_s)
            df.at[idx, 'tecnico'] = tec or df.at[idx, 'tecnico']
            df.at[idx, 'descricao'] = desc or df.at[idx, 'descricao']
            df.at[idx, 'data_inicio'] = dt_f
            df.at[idx, 'status'] = stat  # 👈 AGORA VAI ATUALIZAR
            df.at[idx, 'materiais_checklist'] = txt
            df.at[idx, 'mes_referencia'] = mes
            df.at[idx, 'responsavel'] = resp or df.at[idx, 'responsavel']
            df.at[idx, 'telefone'] = tel
            df.at[idx, 'observacoes'] = obs_f
            df.at[idx, 'valor_acordado'] = valor
        else:
            # 3. SE NÃO ACHOU (mid_s é None ou novo), CRIA NOVA
            nid = str(mid_m) if mid_m else str(mid_s)
            novo_dado = pd.DataFrame([{
                'id_instalacao': nid,
                'tecnico': tec,
                'descricao': desc,
                'data_inicio': dt_f,
                'status': stat,
                'materiais_checklist': txt,
                'mes_referencia': mes,
                'solucao': obs_n,
                'responsavel': resp,
                'telefone': tel,
                'observacoes': obs_f,
                'valor_acordado': valor
            }])
            df = pd.concat([df, novo_dado], ignore_index=True)

    df.to_csv(CSV_FILE, index=False, sep=',', encoding='latin-1')
    return (sig or 0) + 1


@app.callback(
    [Output('filtro-mes', 'options'),
     Output('filtro-mes', 'value')],
    Input('refresh-signal', 'data'),
    State('filtro-mes', 'value')
)
def upd_filter(n, mes_selecionado):
    df = load_data()
    mes_atual = f"{MESES_PT.get(datetime.now().strftime('%B'))}/{datetime.now().year}"

    if df.empty:
        return [{'label': mes_atual, 'value': mes_atual}], mes_atual

    meses = sorted(df['mes_referencia'].unique().tolist(), reverse=True)
    options = [{'label': i, 'value': i} for i in meses]

    # 👉 mantém o mês atual se ainda existir
    if mes_selecionado in meses:
        return options, mes_selecionado

    # 👉 senão, cai para o mais recente
    return options, meses[0]



@app.callback(
    Output('cards-area', 'children'),
    [Input('refresh-signal', 'data'),
     Input('filtro-mes', 'value'),
     Input('search-input', 'value')]
)
def render_cards(sig, mes, search):
    # ... aqui começa o código que lê o CSV de instalações ...
    df = load_data()
    if df.empty: return html.Div("Sem registros.", className="text-center w-100 mt-5 text-muted")
    df_f = df[df['mes_referencia'] == mes]
    if search:
        st = str(search).lower()
        df_f = df_f[
            (df_f['id_instalacao'].str.lower().str.contains(st)) | (df_f['descricao'].str.lower().str.contains(st)) | (
                df_f['tecnico'].str.lower().str.contains(st))]
    cards = []
    agora = datetime.now()
    for _, r in df_f.iterrows():
        t, e = 0, 0
        for i in str(r['materiais_checklist']).split(';'):
            if '|' in i: p = i.split('|'); t += float(p[1]); e += float(p[2])
        perc = int((e / t * 100)) if t > 0 else 0
        c_b = "#ff4d4d" if perc <= 30 else ("#ffcc00" if perc <= 80 else "#2eb82e")
        try:
            d_ag = datetime.strptime(str(r['data_inicio']), "%Y-%m-%d %H:%M")
        except:
            d_ag = agora
        inv = True

        if r['status'] == "Finalizada":
            c_c = "success"  # 🟢 verde
        elif r['status'] in ["Pendente", "Em Andamento"]:
            c_c = "primary"  # 🔵 azul
        elif r['status'] == "Aberta":
            c_c = "secondary"  # ⚪ cinza
            inv = False
        else:
            c_c = "secondary"

        # VALOR NO CARD
        valor_display = r['valor_acordado'] if 'valor_acordado' in r and r['valor_acordado'] else "0,00"

        cards.append(
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader([
                            html.Small(f"Nº O.S: {r['id_instalacao']}", className="fw-bold"),
                            dbc.Badge(r['status'], color="light", text_color="dark", className="float-end")
                        ]),

                        dbc.CardBody(
                            [
                                html.H5(r['descricao'], className="card-title text-truncate"),
                                html.P([html.I(className="bi bi-person me-2"), r['tecnico']], className="mb-1 small"),
                                html.P(
                                    [html.I(className="bi bi-cash-stack me-2"),
                                     html.Strong("Valor: "),
                                     f"R$ {valor_display}"],
                                    className="mb-1 small text-info"
                                ),
                                html.P(
                                    [html.I(className="bi bi-calendar-event me-2"),
                                     d_ag.strftime('%d/%m - %H:%M')],
                                    className="mb-3 small"
                                ),
                                dbc.Progress(
                                    value=perc,
                                    label=f"{perc}%",
                                    animated=True,
                                    striped=True,
                                    style={"height": "18px"},
                                    color=c_b
                                )
                            ],
                            style={
                                "backgroundColor": (
                                    "#198754" if c_c == "success"  # Finalizada
                                    else "#0d6efd" if c_c == "primary"  # Em Andamento
                                    else "#6c757d" if c_c == "warning"  # Aberta
                                    else "#495057"
                                ),
                                "color": "white"
                            }
                        ),

                        dbc.CardFooter(
                            dbc.Button(
                                [html.I(className="bi bi-pencil-square me-2"), "Gerenciar"],
                                id={
                                    'type': 'edit',
                                    'index': str(r['id_instalacao'])
                                },
                                color="dark",
                                size="sm",
                                className="w-100"
                            )
                        )
                    ],
                    color=c_c,
                    inverse=inv,
                    className="h-100 shadow-sm border-0 border-top border-3 border-info"
                )
            )
        )

    return cards


# --- CALLBACKS BASE ---
@app.callback(Output('visualizador-frame', 'src'), Input({'type': 'btn-ver-arquivo', 'filename': ALL}, 'n_clicks'),
              prevent_initial_call=True)
def atualizar_visualizador(n_clicks):
    ctx = callback_context
    if not ctx.triggered or not any(n_clicks): return dash.no_update
    trig_id = json.loads(ctx.triggered[0]['prop_id'].split('.n_clicks')[0])
    return f"/download/{trig_id['filename']}"


@app.callback(Output("btn-salvar-base", "children"),
              Input("btn-salvar-base", "n_clicks"),
              State("editor-texto", "value"),
              prevent_initial_call=True)
def cb_salvar_base(n, texto):
    if n:
        salvar_nota_json(texto)
        return [html.I(className="bi bi-check-all me-2"), "Salvo com Sucesso!"]
    return [html.I(className="bi bi-save me-2"), "Salvar Documentação"]


@app.callback(Output('lista-arquivos-base', 'children'), Input('upload-base', 'contents'),
              State('upload-base', 'filename'), prevent_initial_call=True)
def cb_upload_base(list_of_contents, list_of_names):
    if list_of_contents:
        for content, name in zip(list_of_contents, list_of_names):
            data = content.split(',')[1]
            with open(os.path.join(FOLDER_FILES, name), "wb") as f:
                f.write(base64.b64decode(data))
        return gerar_lista_arquivos(os.listdir(FOLDER_FILES))
    return dash.no_update


@app.callback(Output('resumo-kit-col', 'children'),
              [Input('dropdown-kit-tec', 'value'),
               Input('refresh-kit-signal', 'data')])
def atualizar_progresso_kit(tecnico, sig):
    if not tecnico: return ""
    df_kits = pd.read_csv(CSV_KITS, sep=',', encoding='latin-1')
    dados_tec = df_kits[df_kits['tecnico'] == tecnico]
    if dados_tec.empty: return html.Div(dbc.Badge("Sem dados salvos", color="secondary"), className="mt-4")
    total = len(dados_tec)
    ok = len(dados_tec[(dados_tec['qtd_tem'] > 0) & (dados_tec['qtd_faltante'] == 0)])
    perc = int((ok / total * 100)) if total > 0 else 0
    cor = "danger" if perc <= 30 else ("warning" if perc <= 80 else "success")
    return html.Div([html.Small(f"Integridade do Kit: {ok}/{total}", className="fw-bold text-info"),
                     dbc.Progress(value=perc, label=f"{perc}%", color=cor, striped=True, animated=True,
                                  style={"height": "20px"})], className="mt-3")


def render_aba_agenda():
    return html.Div([
        dbc.Row([
            dbc.Col(dbc.Button([html.I(className="bi bi-plus-circle me-2"), "Nova Manutenção"],
                               id="btn-trigger-agenda", # 👈 MUDAMOS O ID AQUI
                               color="success"), width="auto")
        ], justify="end", className="mb-3"),
        html.Div(id="cards-agenda-area")
    ])

@app.callback(
    [
        Output("agenda-id-manual", "value"),
        Output("agenda-cliente", "value"),
        Output("agenda-tel", "value"),
        Output("agenda-tec", "value"),
        Output("agenda-status", "value"),
        Output("agenda-data", "value"),
        Output("agenda-obs", "value"),
        Output("agenda-info-final", "value"),
    ],
    Input("agenda-id-store", "data"),
    prevent_initial_call=True
)
def carregar_agenda(agenda_id):

    # ➕ NOVA MANUTENÇÃO (modal aberto vazio)
    if not agenda_id:
        return "", "", "", None, "Aberta", "", "", ""

    # 📄 LÊ CSV
    df = pd.read_csv(CSV_AGENDA, sep=",", encoding="latin-1").fillna("").astype(str)

    linha = df[df["id_instalacao"].str.strip() == str(agenda_id).strip()]

    if linha.empty:
        return "", "", "", None, "Aberta", "", "", ""

    r = linha.iloc[0]

    # 🔍 SEPARA PROBLEMA E ENCERRAMENTO (SEM PREFIXO)
    obs_raw = r.get("observacoes", "").strip()

    problema = ""
    encerramento = ""

    if "ENCERRAMENTO:" in obs_raw:
        partes = obs_raw.split("ENCERRAMENTO:", 1)
        problema = partes[0].strip()
        encerramento = partes[1].strip()
    else:
        problema = obs_raw

    return (
        r.get("id_instalacao", ""),
        r.get("descricao", ""),
        r.get("telefone", ""),
        r.get("tecnico") or None,
        r.get("status", "Aberta"),
        r.get("data_inicio", ""),
        problema,
        encerramento,
    )


@app.callback(
    Output("agenda-modal-header", "style"),
    Input("agenda-status", "value"),
)
def cor_header_agenda(status):
    if status == "Pendente":
        cor = "#dc3545"
    elif status == "Finalizada":
        cor = "#198754"
    else:
        cor = None

    return {}


# Callback para mostrar a caixa de encerramento apenas quando for "Resolvido"
@app.callback(
    Output("div-info-final", "style"),
    Input("agenda-status", "value")
)
def mostrar_obs_final(status):
    if status == "Finalizada":
        return {"display": "block"}
    return {"display": "none"}


# Callback para SALVAR os dados da Agenda
@app.callback(
    Output("refresh-signal", "data", allow_duplicate=True),
    Input("agenda-btn-salvar", "n_clicks"),
    [
        State("agenda-id-store", "data"),
        State("agenda-id-manual", "value"),
        State("agenda-cliente", "value"),
        State("agenda-tel", "value"),
        State("agenda-tec", "value"),
        State("agenda-status", "value"),
        State("agenda-data", "value"),
        State("agenda-obs", "value"),
        State("agenda-info-final", "value"),
        State("tabs-agenda-cidades", "active_tab"),
        State("refresh-signal", "data")
    ],
    prevent_initial_call=True
)
def salvar_dados_agenda(
        n, agenda_id, os_id, cliente, tel, tec,
        status, data, obs, info_f, tab, sig
):
    if not n:
        return dash.no_update

    # 🔧 NORMALIZA DATA para YYYY-MM-DD (Garante que o filtro do calendário funcione)
    if data:
        try:
            # Tenta converter vindo do DatePicker (ISO)
            data = datetime.fromisoformat(data.replace('Z', '')).strftime('%Y-%m-%d')
        except:
            data = str(data)[:10]
    else:
        data = date.today().isoformat()

    status = status or "Aberta"
    cidade_tag = "[Divinópolis]" if tab == "ag-div" else "[Itaúna]"

    df = pd.read_csv(CSV_AGENDA, sep=',', encoding='latin-1').fillna("")
    df['id_instalacao'] = df['id_instalacao'].astype(str).str.strip()

    id_busca = str(agenda_id or os_id).strip()

    # 🔥 IMPORTANTE: O render_cards_agenda filtra por "Divinópolis" ou "Itaúna" nas observações.
    # Se não salvarmos a tag da cidade, a ordem NUNCA vai aparecer naquela aba.
    obs_com_cidade = f"{cidade_tag} {obs or ''}"

    if status == "Finalizada" and info_f:
        obs_com_cidade += f" | ENCERRAMENTO: {info_f.strip()}"

    mask = df['id_instalacao'] == id_busca

    if mask.any():
        df.loc[mask, 'id_instalacao'] = str(os_id or id_busca)
        df.loc[mask, 'tecnico'] = tec
        df.loc[mask, 'descricao'] = cliente
        df.loc[mask, 'status'] = status
        df.loc[mask, 'telefone'] = tel or ""
        df.loc[mask, 'observacoes'] = obs_com_cidade  # Salva com a tag da cidade
        df.loc[mask, 'data_inicio'] = data
    else:
        nova_linha = {
            'id': str(datetime.now().timestamp()),
            'id_instalacao': str(os_id or id_busca),
            'tecnico': tec or "",
            'descricao': cliente or "",
            'status': status,
            'telefone': tel or "",
            'observacoes': obs_com_cidade,  # Salva com a tag da cidade
            'data_inicio': data,
            'mes_referencia': f"{MESES_PT.get(datetime.now().strftime('%B'), 'Janeiro')}/{datetime.now().year}"
        }
        df = pd.concat([df, pd.DataFrame([nova_linha])], ignore_index=True)

    df.to_csv(CSV_AGENDA, index=False, sep=',', encoding='latin-1')

    # Retorna o sinal para disparar o render_cards_agenda automaticamente
    return (sig or 0) + 1

@app.callback(
    Output("refresh-signal", "data", allow_duplicate=True),
    Input("agenda-btn-excluir", "n_clicks"),
    State("agenda-id-store", "data"),
    State("refresh-signal", "data"),
    prevent_initial_call=True
)
def excluir_agenda(n, agenda_id, sig):
    if not n or not agenda_id:
        return dash.no_update

    # 1️⃣ LÊ O CSV
    df = pd.read_csv(
        CSV_AGENDA,
        sep=',',
        encoding='latin-1',
        dtype=str  # 👈 ESSENCIAL
    )

    df = df.fillna("")

    # 🔒 GARANTE COLUNA ID
    if 'id' not in df.columns:
        df['id'] = ""

    # Remove a ordem pelo ID
    df = df[df["id_instalacao"].astype(str) != str(agenda_id)]

    df.to_csv(CSV_AGENDA, index=False, sep=",", encoding="latin-1")

    return (sig or 0) + 1

from dash import callback_context, no_update


@app.callback(
    [
        Output("modal-agenda", "is_open"),
        Output("agenda-id-store", "data")
    ],
    [
        Input("btn-nova-agenda", "n_clicks"),
        Input({'type': 'edit-agenda', 'index': ALL}, 'n_clicks'),
        Input("agenda-btn-fechar", "n_clicks"),
        Input("agenda-btn-excluir", "n_clicks"),
        Input("refresh-signal", "data"),  # 🔥 ESSENCIAL
    ],
    [
        State("agenda-id-store", "data"),
        State("modal-agenda", "is_open")
    ],
    prevent_initial_call=True
)
def toggle_agenda(n_nova, n_edit, n_fecha, n_excluir, refresh, agenda_id, is_open):
    ctx = callback_context

    if not ctx.triggered:
        return is_open, dash.no_update

    trig_id = ctx.triggered[0]["prop_id"]

    # 🔒 FECHA AUTOMATICAMENTE APÓS SALVAR
    if "refresh-signal" in trig_id:
        return False, dash.no_update

    # ❌ FECHAR / EXCLUIR
    if "agenda-btn-fechar" in trig_id or "agenda-btn-excluir" in trig_id:
        return False, dash.no_update

    # ➕ NOVA MANUTENÇÃO
    if "btn-nova-agenda" in trig_id:
        return True, None

    # ✏️ GERENCIAR EXISTENTE
    if "edit-agenda" in trig_id:
        # 🛡️ PROTEÇÃO: só abre se realmente clicou
        if not n_edit or sum(c or 0 for c in n_edit) == 0:
            return is_open, dash.no_update

        clean = trig_id.split(".n_clicks")[0]
        agenda_dict = json.loads(clean)
        return True, str(agenda_dict["index"])

    return is_open, dash.no_update


@app.callback(
    Output("btn-nova-agenda", "n_clicks"),
    [Input("btn-trigger-agenda", "n_clicks")],
    prevent_initial_call=True
)
def repassar_clique(n):
    return n


@app.callback(
    Output("cards-agenda-area", "children"),
    [
        Input("refresh-signal", "data"),
        Input("tabs-agenda-cidades", "active_tab"),
        Input("agenda-data-selecionada", "date")  # 📅 CALENDÁRIO
    ]
)
def render_cards_agenda(sig, tab, data_selecionada):
    if not os.path.exists(CSV_AGENDA):
        return html.Div("CSV não encontrado.")

    if not data_selecionada:
        return html.Div(
            "Selecione uma data no calendário",
            className="text-center text-muted mt-5"
        )

    df = pd.read_csv(CSV_AGENDA, sep=',', encoding='latin-1')
    df['observacoes'] = df['observacoes'].fillna("")
    df['data_inicio'] = df['data_inicio'].fillna("")

    cidade_alvo = "Divinópolis" if tab == "ag-div" else "Itaúna"

    # 1. FILTRO DE CIDADE (Adicionado para as ordens aparecerem na aba certa)
    df_f = df[df['observacoes'].str.contains(cidade_alvo, case=False)]

    # 2. CONVERTE DATA DO CSV PARA yyyy-mm-dd
    df_f['data_ref'] = pd.to_datetime(
        df_f['data_inicio'],
        errors='coerce'
    ).dt.date.astype(str)

    # 3. FILTRO PELO DIA SELECIONADO (Agora dentro do DF já filtrado por cidade)
    df_f = df_f[df_f['data_ref'] == str(data_selecionada)]

    # 🔥 GARANTE UM CARD POR O.S.
    df_f = (
        df_f
        .sort_values('data_inicio', ascending=False)
        .drop_duplicates(subset=['id_instalacao'], keep='first')
    )

    if df_f.empty:
        return html.Div(
            f"Nenhuma manutenção para {cidade_alvo} nesta data.",
            className="text-center w-100 mt-5 text-muted"
        )

    colunas_por_tecnico = []
    tecnicos_ativos = df_f['tecnico'].dropna().unique()

    for tecnico in tecnicos_ativos:
        df_tecnico = df_f[df_f['tecnico'] == tecnico]
        cards_do_tecnico = []

        header_tecnico = html.Div(
            str(tecnico).upper(),
            style={
                "backgroundColor": "#2c3e50",
                "color": "white",
                "textAlign": "center",
                "padding": "10px",
                "borderRadius": "5px",
                "marginBottom": "15px",
                "fontWeight": "bold",
                "borderBottom": "3px solid #17a2b8",
                "width": "300px"
            }
        )

        for _, r in df_tecnico.iterrows():
            status_atual = str(r.get('status', '')).strip()
            c_c = (
                "success" if status_atual == "Finalizada"
                else "danger" if status_atual == "Pendente"
                else "secondary" if status_atual == "Aberta"
                else "warning"
            )

            data_exibicao = r['data_inicio'] if r['data_inicio'] else "Não definida"

            # 🔎 TRATAMENTO DA OBSERVAÇÃO (PROBLEMA LIMPO)
            obs_raw = str(r.get('observacoes', ''))
            problema_texto = (
                obs_raw.split('|')[0]
                .replace('PROBLEMA:', '')
                .replace(f'[{cidade_alvo}]', '')
                .strip()
            )

            card = dbc.Card(
                [
                    dbc.CardHeader(
                        [
                            html.Small(f"Nº O.S: {r['id_instalacao']}", className="fw-bold"),
                            dbc.Badge(status_atual, color="light", text_color="dark", className="float-end")
                        ],
                        style={
                            "backgroundColor": "#212529",
                            "borderBottom": "2px solid rgba(255,255,255,0.1)"
                        }
                    ),

                    dbc.CardBody(
                        [
                            html.H5(
                                r['descricao'],
                                className="card-title text-truncate",
                                style={"fontWeight": "bold"}
                            ),
                            html.P(
                                [html.I(className="bi bi-person me-2"), f"Técnico: {tecnico}"],
                                className="mb-1 small"
                            ),
                            html.P(
                                [html.I(className="bi bi-calendar-event me-2"), data_exibicao],
                                className="mb-2 small"
                            ),

                            html.Div(
                                [
                                    html.Strong(
                                        "Problema: ",
                                        className="small",
                                        style={"color": "#adb5bd"}
                                    ),
                                    html.P(
                                        problema_texto if problema_texto else "Não informado",
                                        className="small mb-0",
                                        style={
                                            "fontStyle": "italic",
                                            "display": "block",
                                            "height": "40px",
                                            "overflow": "hidden"
                                        }
                                    )
                                ],
                                className="p-2 mb-2",
                                style={
                                    "backgroundColor": "rgba(0,0,0,0.2)",
                                    "borderRadius": "5px"
                                }
                            )
                        ]
                    ),

                    dbc.CardFooter(
                        dbc.Button(
                            "Gerenciar",
                            id={'type': 'edit-agenda', 'index': str(r['id_instalacao'])},
                            color="light",
                            size="sm",
                            className="w-100"
                        ),
                        style={"backgroundColor": "#212529"}
                    )
                ],
                color=c_c,
                inverse=True,
                className="mb-3 shadow border-0",
                style={"width": "300px"}
            )

            cards_do_tecnico.append(card)

        colunas_por_tecnico.append(
            dbc.Col(
                [header_tecnico, html.Div(cards_do_tecnico)],
                width="auto",
                className="px-3 border-end border-secondary"
            )
        )

    return dbc.Row(
        colunas_por_tecnico,
        className="d-flex flex-nowrap overflow-auto py-3 m-0",
        style={"width": "100%"}
    )



# 🔐 REGISTRA COMPONENTES DINÂMICOS (OBRIGATÓRIO)
app.validation_layout = html.Div([
    modal_principal,
    modal_agenda,
    modal_pergunta_finalizar,
    confirm_modal_inst,
    confirm_clear_all,
    modal_conf_item_unico
])

if __name__ == '__main__':
    app.run(debug=True, port=8050)
