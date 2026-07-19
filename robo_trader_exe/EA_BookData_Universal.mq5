//+------------------------------------------------------------------+
//| EA_BookData_Universal.mq5                                        |
//| EA Universal para capturar dados do book (WDO e WIN)            |
//| Compatível com monstro_unificado.py e monstro_unificado_v2.py   |
//+------------------------------------------------------+
#property copyright "Monstro Trading System"
#property version   "2.00"
#property description "EA Universal para capturar book de ofertas - WDO e WIN"

// Parâmetros de entrada
input string InpSymbol = "";  // Símbolo (vazio = símbolo atual do gráfico)
input int InpUpdateInterval = 100;  // Intervalo de atualização em ms
input bool InpDebugMode = false;    // Modo debug (mais logs)

// Variáveis globais
string g_symbol;
int g_fileHandle = INVALID_HANDLE;
datetime g_lastUpdate = 0;
int g_updateCount = 0;

//+------------------------------------------------------------------+
//| Função de inicialização do EA                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    // Define o símbolo
    g_symbol = (InpSymbol == "") ? Symbol() : InpSymbol;

    Print("🤖 EA BookData Universal iniciado para símbolo: ", g_symbol);
    Print("📊 Configurações: Intervalo=", InpUpdateInterval, "ms, Debug=", InpDebugMode);

    // Verifica se o símbolo existe
    if(!SymbolSelect(g_symbol, true))
    {
        Print("❌ ERRO: Símbolo ", g_symbol, " não encontrado!");
        return INIT_FAILED;
    }

    // Ativa o book de ofertas
    if(!MarketBookAdd(g_symbol))
    {
        Print("❌ ERRO: Não foi possível ativar o book para ", g_symbol);
        return INIT_FAILED;
    }

    // Identifica o tipo de contrato
    string contractType = "";
    if(StringFind(g_symbol, "WDO") >= 0)
        contractType = "WDO (Mini Dólar)";
    else if(StringFind(g_symbol, "WIN") >= 0)
        contractType = "WIN (Mini Índice)";
    else
        contractType = "Outro";

    Print("✅ Book ativado com sucesso para ", g_symbol, " - Tipo: ", contractType);

    // Cria arquivo CSV
    string fileName = "book_data.csv";
    g_fileHandle = FileOpen(fileName, FILE_WRITE|FILE_TXT|FILE_ANSI);

    if(g_fileHandle == INVALID_HANDLE)
    {
        Print("❌ ERRO: Não foi possível criar arquivo ", fileName);
        return INIT_FAILED;
    }

    Print("📁 Arquivo criado: ", fileName);

    // Timer para atualização contínua
    EventSetTimer(InpUpdateInterval / 1000.0);  // Converte ms para segundos

    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Função de finalização do EA                                     |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    // Remove o book
    MarketBookRelease(g_symbol);

    // Fecha arquivo
    if(g_fileHandle != INVALID_HANDLE)
    {
        FileClose(g_fileHandle);
        g_fileHandle = INVALID_HANDLE;
    }

    // Para o timer
    EventKillTimer();

    Print("🔴 EA BookData Universal finalizado. Updates processados: ", g_updateCount);
}

//+------------------------------------------------------------------+
//| Função do timer                                                 |
//+------------------------------------------------------------------+
void OnTimer()
{
    UpdateBookData();
}

//+------------------------------------------------------------------+
//| Função principal para atualizar dados do book                  |
//+------------------------------------------------------------------+
void UpdateBookData()
{
    MqlBookInfo book[];

    // Obtém dados do book
    if(!MarketBookGet(g_symbol, book))
    {
        if(InpDebugMode)
            Print("⚠️ Falha ao obter book para ", g_symbol);
        return;
    }

    if(ArraySize(book) == 0)
    {
        if(InpDebugMode)
            Print("⚠️ Book vazio para ", g_symbol);
        return;
    }

    // Separa volumes de BID e ASK
    string bidVolumes = "";
    string askVolumes = "";

    int bidCount = 0;
    int askCount = 0;
    long totalBidVolume = 0;
    long totalAskVolume = 0;

    for(int i = 0; i < ArraySize(book); i++)
    {
        if(book[i].type == BOOK_TYPE_BUY)  // BID
        {
            if(bidCount > 0) bidVolumes += ",";
            bidVolumes += IntegerToString(book[i].volume);
            totalBidVolume += book[i].volume;
            bidCount++;
        }
        else if(book[i].type == BOOK_TYPE_SELL)  // ASK
        {
            if(askCount > 0) askVolumes += ",";
            askVolumes += IntegerToString(book[i].volume);
            totalAskVolume += book[i].volume;
            askCount++;
        }
    }

    // Reabre arquivo para escrita (sobrescreve)
    if(g_fileHandle != INVALID_HANDLE)
        FileClose(g_fileHandle);

    g_fileHandle = FileOpen("book_data.csv", FILE_WRITE|FILE_TXT|FILE_ANSI);

    if(g_fileHandle != INVALID_HANDLE)
    {
        // Escreve dados no formato esperado pelo Python
        FileWrite(g_fileHandle, bidVolumes);   // Linha 1: volumes BID
        FileWrite(g_fileHandle, askVolumes);   // Linha 2: volumes ASK

        FileFlush(g_fileHandle);
        FileClose(g_fileHandle);
        g_fileHandle = INVALID_HANDLE;
    }

    g_updateCount++;

    // Log periódico (a cada 100 updates ou se debug ativo)
    if(InpDebugMode || (g_updateCount % 100 == 0))
    {
        datetime now = TimeCurrent();
        Print("📊 [", TimeToString(now), "] ", g_symbol,
              " - BIDs: ", bidCount, " (", totalBidVolume, "cc)",
              " | ASKs: ", askCount, " (", totalAskVolume, "cc)",
              " | Updates: ", g_updateCount);
    }
}

//+------------------------------------------------------------------+
//| Função de tick (backup para alta frequência)                   |
//+------------------------------------------------------------------+
void OnTick()
{
    // Atualiza apenas se passou tempo suficiente
    datetime now = TimeCurrent();
    if(now != g_lastUpdate)
    {
        UpdateBookData();
        g_lastUpdate = now;
    }
}

//+------------------------------------------------------------------+
//| Função para eventos do book                                     |
//+------------------------------------------------------------------+
void OnBookEvent(const string& symbol)
{
    if(symbol == g_symbol)
    {
        UpdateBookData();
    }
}
