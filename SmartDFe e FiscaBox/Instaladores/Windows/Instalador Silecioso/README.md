# SmartDFe — instalação silenciosa (SemE1) 1.4.85

Instalador para ser executado sem assistente, recebendo o Client ID por parâmetro. Feito para ser embutido no instalador do integrador.

Se o Client ID não for informado, **a instalação aborta antes de copiar qualquer arquivo** — nenhum serviço é criado e nada é gravado em disco.

## Como instalar

```
SmartDFeSilencioso_SemE1_1.4.85.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLIENTID=SEU_CLIENT_ID /LOG="%TEMP%\smartdfe_install.log"
```

Requer elevação (Administrador). Se o processo que chama já estiver elevado, não há UAC adicional.

### Parâmetros

| Parâmetro | Obrigatório | Descrição |
|---|---|---|
| `/CLIENTID=<valor>` | **Sim** | Client ID do Veraciti. |
| `/VERYSILENT` | Sim | Instala sem assistente e sem barra de progresso. |
| `/SUPPRESSMSGBOXES` | Recomendado | Suprime caixas de diálogo. |
| `/NORESTART` | Recomendado | Não reinicia a máquina ao final. |
| `/LOG="<caminho>"` | Recomendado | Grava o log da instalação. É o primeiro lugar a olhar em caso de falha. |

Destino fixo: `C:\Program Files (x86)\SmartDFe`.

## Como saber se deu certo

**1. Código de saída.** `0` = sucesso. Qualquer outro valor = falhou.

| Código | Significado |
|---|---|
| `0` | Sucesso |
| `1` | Não conseguiu inicializar |
| `2` | Erro fatal antes de instalar |
| `3` | Erro fatal durante a instalação |
| `5` | Cancelado |
| `7` | Pré-checagem recusou continuar |
| `8` | Precisa reiniciar para concluir |

**2. Arquivo de resultado** — `C:\smartnfce\smartdfe_install_result.json`

| Campo | Significado |
|---|---|
| `ok` | `true` = instalado e provisionado; `false` = falhou. |
| `erro` | Motivo da falha, quando `ok` é `false`. |

O arquivo pode conter outros campos: trate `ok` e `erro` como o contrato mínimo.

**3. Health check** — `http://127.0.0.1:8780/api/v1/health`

Resposta esperada:

```json
{
  "status": "ok",
  "motor": { "online": true },
  "contingencia": { "pendentes": 0 },
  "certificado": { "dias_para_vencer": 60 }
}
```

## Embutindo no seu instalador

Seção `[Run]`:

```ini
[Run]
Filename: "{tmp}\SmartDFeSilencioso_SemE1_1.4.85.exe"; \
  Parameters: "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLIENTID={code:GetClientId} /LOG=""{tmp}\smartdfe_install.log"""; \
  StatusMsg: "Instalando SmartDFe..."; \
  Flags: waituntilterminated
```

Se precisar decidir com base no resultado, use `[Code]`:

```pascal
[Code]
function InstalarSmartDFe(const ClientId: string): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec(
    ExpandConstant('{tmp}\SmartDFeSilencioso_SemE1_1.4.85.exe'),
    '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLIENTID=' + ClientId +
      ' /LOG="' + ExpandConstant('{tmp}\smartdfe_install.log') + '"',
    '', SW_SHOW, ewWaitUntilTerminated, ResultCode);

  Result := Result and (ResultCode = 0);
end;
```

`waituntilterminated` é obrigatório: sem ele, seu instalador continuaria antes do SmartDFe terminar.

Sequência: executar → exigir código `0` → confirmar `"ok": true` no JSON → seguir com o restante da sua instalação.

## O que é instalado

Serviços: `SmartNFCeEmissor`, `SmartNFCeContingencia`, `SmartDFeHub`, `SmartUpdater` (todos em execução automática).

Portas: `3001`, `3002`, `8765`, `8780`.

O serviço `E1APINotas` e a porta `4001` **não fazem parte desta variante** — nesta versão o DANFE é gerado pelo próprio motor. A ausência deles é esperada.

## Desinstalação

```
"C:\Program Files (x86)\SmartDFe\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES
```

O nome pode variar (`unins000.exe`, `unins001.exe`…); confira o arquivo presente na pasta.

## Se falhar

- Leia o campo `erro` do JSON e o log indicado em `/LOG`.
- Código `1` com nada instalado normalmente é parâmetro inválido ou ausência de elevação.
- Serviços criados mas sem provisionar costumam indicar Client ID inválido — verifique o valor passado em `/CLIENTID`.
