//+------------------------------------------------------------------+
//| EA_BookData_WIN_DINAMI5                                     |
//| EA DINÂMICO para WIN - Seleciona contrato automaticamente       |
//| Compatível com monstro_unificado_v2.py (seleção dinâmica)       |
//+------------------------------------------------------------------+
#property copyright "Monstro Trading System"
#property version   "2.00"
#property description "EA WIN DINÂMICO - Seleciona contrato front-month automaticamente"

// Parâmetros de entrada
input int InpUpdateInterval = 100;  // Intervalo de atualização em ms
input bool InpDebugMode = false;    // Modo debug (mais logs)

// Variáveis globais
string g_symbol;
int g_fileHandle = INVALID_HANDLE;
datetime g_lastUpdate = 0;
int g_updateCount = 0;
bool g_bookActive = false;
datetime g_lastSymbolCheck = 0;
int g_symbolCheckInterval = 300; // Verifica símbolo a cada 5 minutos

//+------------------------------------------------------------------+
//| Função para encontrar contrato WIN ativo DINÂMICO               |
//+------------------------------------------------------------------+
string FindActiveDynamicWINContract()
{
    Print("🔍 Procurando contrato WIN front-month dinâmico...");

    // Lista para armazenar candidatos
    string candidates[];
    datetime candidateExpirations[];
    int candidateCount = 0;

    // Busca em todos os símbolos
    int totalSymbols = SymbolsTotal(false);
    datetime currentTime = TimeCurrent();

    for(int i = 0; i < totalSymbols; i++)
    {
        string symbol = SymbolName(i, false);

        // Verifica se é contrato WIN mensal (formato: WIN + letra + 2 dígitos)
        if(StringLen(symbol) == 6 && StringSubstr(symbol, 0, 3) == "WIN")
        {
            string monthCode = StringSubstr(symbol, 3, 1);
            string yearCode = StringSubstr(symbol, 4, 2);

            // Verifica se é formato válido (letra + 2 números)
            if((monthCode >= "A" && monthCode <= "Z") &&
               StringToInteger(yearCode) >= 0)
            {
                // Verifica se está ativo para trading
                if(SymbolInfoInteger(symbol, SYMBOL_TRADE_MODE) == SYMBOL_TRADE_MODE_FULL)
                {
                    // Obtém data de expiração
                    datetime expiration = (datetime)SymbolInfoInteger(symbol, SYMBOL_EXPIRATION_TIME);

                    // Só considera contratos que ainda não venceram
                    if(expiration > currentTime)
                    {
                        // Adiciona à lista de candidatos
                        ArrayResize(candidates, candidateCount + 1);
                        ArrayResize(candidateExpirations, candidateCount + 1);

                        candidates[candidateCount] = symbol;
                        candidateExpirations[candidateCount] = expiration;
                        candidateCount++;

                        Print("📊 Candidato encontrado: ", symbol, " (exp: ", TimeToString(expiration), ")");
                    }
                }
            }
        }
    }

    if(candidateCount == 0)
    {
        Print("❌ Nenhum contrato WIN ativo encontrado!");
        return "";
    }

    // Encontra o contrato com expiração mais próxima (front-month)
    string frontMonth = candidates[0];
    datetime earliestExpiration = candidateExpirations[0];

    for(int i = 1; i < candidateCount; i++)
    {
        if(candidateExpirations[i] < earliestExpiration)
        {
            frontMonth = candidates[i];
            earliestExpiration = candidateExpirations[i];
        }
    }

    Print("🎯 Contrato front-month selecionado: ", frontMonth);
    Print("📅 Expiração: ", TimeToString(earliestExpiration));

    return frontMonth;
}

//+------------------------------------------------------------------+
//| Função para verificar se precisa trocar de contrato             |
//+------------------------------------------------------------------+
bool CheckIfNeedSymbolChange()
{
    datetime now = TimeCurrent();

    // Verifica apenas a cada intervalo definido
    if(now - g_lastSymbolCheck < g_symbolCheckInterval)
        return false;

    g_lastSymbolCheck = now;

    // Verifica se o contrato atual ainda é válido
    if(g_symbol != "")
    {
        datetime expiration = (datetime)SymbolInfoInteger(g_symbol, SYMBOL_EXPIRATION_TIME);
        int daysToExpiration = (int)((expiration - now) / 86400); // 86400 = segundos em um dia

        Print("📅 Contrato atual: ", g_symbol, " expira em ", daysToExpiration, " dias");

        // Se faltam menos de 2 dias para expirar, procura novo contrato
        if(daysToExpiration < 2)
        {
            Print("⚠️ Contrato próximo do vencimento, procurando novo...");
            return true;
        }

        // Verifica se ainda está ativo para trading
        if(SymbolInfoInteger(g_symbol, SYMBOL_TRADE_MODE) != SYMBOL_TRADE_MODE_FULL)
        {
            Print("⚠️ Contrato não está mais ativo para trading");
            return true;
        }
    }

    return false;
}

//+------------------------------------------------------------------+
//| Função para trocar de contrato dinamicamente                    |
//+------------------------------------------------------------------+
bool SwitchToNewContract()
{
    Print("🔄 Trocando para novo contrato...");

    // Remove book do contrato atual
    if(g_bookActive && g_symbol != "")
    {
        MarketBookRelease(g_symbol);
        g_bookActive = false;
        Print("📚 Book removido do contrato anterior: ", g_symbol);
    }

    // Encontra novo contrato
    string newSymbol = FindActiveDynamicWINContract();

    if(newSymbol == "")
    {
        Print("❌ Não foi possível encontrar novo contrato!");
        return false;
    }

    // Se é o mesmo contrato, não precisa trocar
    if(newSymbol == g_symbol)
    {
        Print("✅ Contratainda é o melhor: ", g_symbol);

        // Reativa book se necessário
        if(!g_bookActive)
        {
            if(MarketBookAdd(g_symbol))
            {
                g_bookActive = true;
                Print("📚 Book reativado para: ", g_symbol);
            }
        }
        return true;
    }

    // Atualiza para novo contrato
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
    Print("🚀 EA BookData WIN DINÂMICO iniciando...");

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
    if(!MarketBookAdd(g_symbol))
    {
        Print("❌ Não foi possível ativar book para ", g_symbol);
        Print("💡 Dica: Verifique se o símbolo suporta book de ofertas");
        return INIT_FAILED;
    }

    g_bookActive = true;
    Print("✅ Book WIN ativado com sucesso para ", g_symbol);

    // Cria arquivo CSV
    string fileName = "book_data_win.csv";
    g_fileHandle = FileOpen(fileName, FILE_WRITE|FILE_TXT|FILE_ANSI);
    if(g_fileHandle == INVALID_HANDLE)
    {
        Print("❌ Não foi possível criar arquivo ", fileName);
        return INIT_FAILED;
    }

    Print("📄 Arquivo WIN criado: ", fileName);
    Print("🔄 EA funcionará com seleção dinâmica de contratos!");

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

    // Fecha arquivo
    if(g_fileHandle != INVALID_HANDLE)
    {
        FileClose(g_fileHandle);
        g_fileHandle = INVALID_HANDLE;
    }

    // Para o timer
    EventKillTimer();

    Print("🏁 EA BookData WIN DINÂMICO finalizado. Updates: ", g_updateCount);
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
//| Função principal para atualizar dados do book                  |
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
            if(bidCount > 0)
                bidVolumes += ",";
            bidVolumes += IntegerToString(book[i].volume);
            totalBidVolume += book[i].volume;
            bidCount++;
        }
        else if(book[i].type == BOOK_TYPE_SELL)  // ASK
        {
            if(askCount > 0)
                askVolumes += ",";
            askVolumes += IntegerToString(book[i].volume);
            totalAskVolume += book[i].volume;
            askCount++;
        }
    }

    // Reabre arquivo para escrita (sobrescreve)
    if(g_fileHandle != INVALID_HANDLE)
        FileClose(g_fileHandle);

    g_fileHandle = FileOpen("book_data_win.csv", FILE_WRITE|FILE_TXT|FILE_ANSI);
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

    // Log periódico com informações do contrato dinâmico
    if(InpDebugMode || (g_updateCount % 100 == 0))
    {
        datetime now = TimeCurrent();
        datetime expiration = (datetime)SymbolInfoInteger(g_symbol, SYMBOL_EXPIRATION_TIME);
        int daysToExp = (int)((expiration - now) / 86400);

        Print("📊 WIN ", g_symbol, " [", TimeToString(now), "] BIDs: ", bidCount,
              " (", totalBidVolume, "cc) | ASKs: ", askCount, " (", totalAskVolume, "cc)");
        Print("📅 Expira em ", daysToExp, " dias");
    }
}

//+------------------------------------------------------------------+
//| Função de tick - Funciona independente da tela                 |
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
//| Função para eventos do book       |
//+------------------------------------------------------------------+
void OnBookEvent(const string& symbol)
{
    if(symbol == g_symbol)
    {
        UpdateBookData();
    }
}
