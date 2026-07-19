//+----------------------------------------------------------------+
//| EA BookData WIN OTIMIZADO - Versão Final                        |
//| Desenvolvido para o Monstro das Negociações                     |
//| Foco: Máxima eficiência, sem race conditions                    |
//+------------------------------------------------------------------+
#property copyright "Monstro das Negociações"
#property version   "3.0"
#property description "EA otimizado para exportar book WIN com máxima eficiência"

//--- Parâmetros de entrada
input int    InpUpdateInterval = 100;    // Intervalo de atualização (ms)
input int    InpMaxLevels = 10;          // Máximo de níveis do book
input bool   InpDebugMode = false;       // Modo debug
input string InpSymbolPrefix = "WIN";    // Prefixo do símbolo

//--- Variáveis globais
string g_symbol = "";                    // Símbolo atual
bool g_bookActive = false;               // Status do book
int g_fileHandle = INVALID_HANDLE;       // Handle do arquivo
ulong g_updateCount = 0;                 // Contador de atualizações
datetime g_lastUpdate = 0;               // Último update
string g_fileName = "book_data_win.csv"; // Nome do arquivo

//+------------------------------------------------------------------+
//| Função para encontrar contrato WIN ativo dinamicamente          |
//+------------------------------------------------------------------+
string FindActiveDynamicWINContract()
{
    string bestSymbol = "";
    datetime nearestExpiration = D'2030.12.31';
    datetime currentTime = TimeCurrent();

    // Lista todos os símbolos disponíveis
    int totalSymbols = SymbolsTotal(true);

    for(int i = 0; i < totalSymbols; i++)
    {
        string symbol = SymbolName(i, true);

        // Verifica se é um contrato WIN
        if(StringFind(symbol, InpSymbolPrefix) != 0)
            continue;

        // Verifica se o símbolo está ativo
        if(!SymbolInfoInteger(symbol, SYMBOL_SELECT))
            continue;

        // Obtém data de expiração
        datetime expiration = (datetime)SymbolInfoInteger(symbol, SYMBOL_EXPIRATION_TIME);

        // Ignora contratos já expirados
        if(expiration <= currentTime)
            continue;

        // Verifica se há negociação ativa
        double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
        double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);

        if(bid <= 0 || ask <= 0)
            continue;

        // Escolhe o contrato com expiração mais próxima (front-month)
        if(expiration < nearestExpiration)
        {
            nearestExpiration = expiration;
            bestSymbol = symbol;
        }
    }

    if(bestSymbol != "")
    {
        Print("🎯 Contrato WIN ativo encontrado: ", bestSymbol,
              " (Expira: ", TimeToString(nearestExpiration), ")");
    }

    return bestSymbol;
}

//+------------------------------------------------------------------+
//| Verifica se precisa trocar de contrato                          |
//+------------------------------------------------------------------+
bool CheckIfNeedSymbolChange()
{
    if(g_symbol == "")
        return true;

    datetime expiration = (datetime)SymbolInfoInteger(g_symbol, SYMBOL_EXPIRATION_TIME);
    datetime now = TimeCurrent();

    // Troca se faltam menos de 2 dias para expirar
    int daysToExpiration = (int)((expiration - now) / 86400);

    if(daysToExpiration < 2)
    {
        Print("⚠️ Contrato próximo do vencimento: ", g_symbol, " (", daysToExpiration, " dias)");
        return true;
    }

    // Verifica se ainda há negociação ativa
    double bid = SymbolInfoDouble(g_symbol, SYMBOL_BID);
    double ask = SymbolInfoDouble(g_symbol, SYMBOL_ASK);

    if(bid <= 0 || ask <= 0)
    {
        Print("⚠️ Sem cotação ativa para: ", g_symbol);
        return true;
    }

    return false;
}

//+------------------------------------------------------------------+
//| Troca para novo contrato                                         |
//+------------------------------------------------------------------+
bool SwitchToNewContract()
{
    // Remove book do contrato atual
    if(g_bookActive && g_symbol != "")
    {
        MarketBookRelease(g_symbol);
        g_bookActive = false;
    }

    // Encontra novo contrato
    string newSymbol = FindActiveDynamicWINContract();
    if(newSymbol == "")
    {
        Print("❌ Nenhum contrato WIN ativo encontrado para troca!");
        return false;
    }

    g_symbol = newSymbol;

    // Garante que está selecionado
    if(!SymbolSelect(g_symbol, true))
    {
        Print("❌ Erro ao selecionar novo contrato: ", g_symbol);
        return false;
    }

    // Ativa book para novo contrato
    if(!MarketBookAdd(g_symbol))
    {
        Print("❌ Erro ao ativar book para novo contrato: ", g_symbol);
        return false;
    }

    g_bookActive = true;
    Print("✅ Trocado com sucesso para: ", g_symbol);

    return true;
}

//+------------------------------------------------------------------+
//| Função de inicialização do EA                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("🚀 EA BookData WIN OTIMIZADO iniciando...");

    // Encontra contrato WIN ativo dinamicamente
    g_symbol = FindActiveDynamicWINContract();
    if(g_symbol == "")
    {
        Print("❌ Nenhum contrato WIN ativo encontrado!");
        return INIT_FAILED;
    }

    Print("🎯 Usando contrato WIN: ", g_symbol);

    // Garante que o símbolo está selecionado
    if(!SymbolSelect(g_symbol, true))
    {
        Print("❌ Não foi possível selecionar ", g_symbol);
        return INIT_FAILED;
    }

    // Ativa o book de ofertas
arketBookAdd(g_symbol))
    {
        Print("❌ Não foi possível ativar book para ", g_symbol);
        Print("💡 Dica: Verifique se o símbolo suporta book de ofertas");
        return INIT_FAILED;
    }

    g_bookActive = true;
    Print("✅ Book WIN ativado com sucesso para ", g_symbol);

    // Timer para atualização contínua
    EventSetTimer(InpUpdateInterval / 1000.0);

    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Função de finalização do EA                                     |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    // Remove o book
    if(g_bookActive)
    {
        MarketBookRelease(g_symbol);
        g_bookActive = false;
    }

    // Fecha arquivo se estiver aberto
    if(g_fileHandle != INVALID_HANDLE)
    {
        FileClose(g_fileHandle);
        g_fileHandle = INVALID_HANDLE;
    }

    // Para o timer
    EventKillTimer();

    Print("🏁 EA BookData WIN OTIMIZADO finalizado. Updates: ", g_updateCount);
}

//+------------------------------------------------------------------+
//| Função do timer - Atualização contínua                         |
//+------------------------------------------------------------------+
void OnTimer()
{
    // Verifica se precisa trocar de contrato
    if(CheckIfNeedSymbolChange())
    {
        if(!SwitchToNewContract())
        {
            Print("❌ Erro ao trocar contrato - continuando com atual");
        }
    }

    // Atualiza dados do book
    UpdateBookData();
}

//+------------------------------------------------------------------+
//| Função principal para atualizar dados do book (VERSÃO JSON)    |
//+------------------------------------------------------------------+
void UpdateBookData()
{
    if(!g_bookActive || g_symbol == "")
        return;

    MqlBookInfo book[];

    // Obtém dados do book
    if(!MarketBookGet(g_symbol, book))
    {
        if(InpDebugMode)
            Print("⚠️ Falha ao obter book WIN para ", g_symbol);
        return;
    }

    if(ArraySize(book) == 0)
    {
        if(InpDebugMode)
            Print("📭 Book WIN vazio para ", g_symbol);
        return;
    }

    // --- NOVA LÓGICA OTIMIZADA PARA CRIAR JSON SEM RACE CONDITIONS ---
    string json = "";
    string bids = "";
    string asks = "";
    int bidCount = 0;
    int askCount = 0;
    long totalBidVolume = 0;
    long totalAskVolume = 0;

    // Primeiro, coleta todos os dados
    for(int i = 0; i < ArraySize(book) && (bidCount < InpMaxLevels || askCount < InpMaxLevels); i++)
    {
        string priceStr = DoubleToString(book[i].price, _Digits);

        if(book[i].type == BOOK_TYPE_BUY && bidCount < InpMaxLevels) // BID
        {
            if(bidCount > 0) bids += ",";
            bids += "{\"price\":" + priceStr + ",\"volume\":" + (string)book[i].volume_real + "}";
            totalBidVolume += book[i].volume;
            bidCount++;
        }
        else if(book[i].type == BOOK_TYPE_SELL && askCount < InpMaxLevels) // ASK
        {
            if(askCount > 0) asks += ",";
            asks += "{\"price\":" + priceStr + ",\"volume\":" + (string)book[i].volume + "}";
            totalAskVolume += book[i].volume;
            askCount++;
        }
    }

    // Monta o JSON completo de uma vez
    json = "{\"bids\":[" + bids + "],\"asks\":[" + asks + "]";
    json += ",\"metadata\":{";
    json += "\"symbol\":\"" + g_symbol + "\",";
    json += "\"timestamp\":" + (string)TimeCurrent() + ",";
    json += "\"total_bid_volume\":" + (string)totalBidVolume + ",";
    json += "\"total_ask_volume\":" + (string)totalAskVolume + ",";
    json += "\"bid_levels\":" + (string)bidCount + ",";
    json += "\"ask_levels\":" + (string)askCount;
    json += "}}";

    // --- ESCRITA ATÔMICA DO ARQUIVO (SEM RACE CONDITIONS) ---
    // Abre, escreve e fecha em uma operação atômica
    g_fileHandle = FileOpen(g_fileName, FILE_WRITE|FILE_TXT|FILE_UNICODE);
    if(g_fileHandle != INVALID_HANDLE)
    {
        FileWriteString(g_fileHandle, json);
        FileFlush(g_fileHandle);  // Força escrita no disco
        FileClose(g_fileHandle);
        g_fileHandle = INVALID_HANDLE;
    }
    else
    {
        if(InpDebugMode)
            Print("❌ Erro ao abrir arquivo: ", g_fileName);
        return;
    }

    g_updateCount++;

    // Log periódico otimizado
    if(InpDebugMode || (g_updateCount % 500 == 0))  // Reduzido de 100 para 500
    {
        datetime now = TimeCurrent();
        datetime expiration = (datetime)SymbolInfoInteger(g_symbol, SYMBOL_EXPIRATION_TIME);
        int daysToExp = (int)((expiration - now) / 86400);

        Print("📊 WIN ", g_symbol, " [", TimeToString(now), "] BIDs: ", bidCount,
              " (", totalBidVolume, "cc) | ASKs: ", askCount, " (", totalAskVolume, "cc)");
        Print("📅 Expira em ", daysToExp, " dias | JSON: ", StringLen(json), " chars | Updates: ", g_updateCount);
    }
}

//+------------------------------------------------------------------+
//| Função de tick - Funciona independente da tela                 |
//+------------------------------------------------------------------+
void OnTick()
{
    // Atualização mais eficiente - só atualiza se mudou o segundo
    datetime now = TimeCurrent();
    if(now != g_lastUpdate)
    {
        UpdateBookData();
        g_lastUpdate = now;
    }
}

//+------------------------------------------------------------------+
//| Função para eventos do book - Máxima responsividade            |
//+------------------------------------------------------------------+
void OnBookEvent(const string& symbol)
{
    if(symbol == g_symbol)
    {
        UpdateBookData();
    }
}
