# Clipper AI

## Upload local de vídeos grandes

O backend aceita uploads locais em streaming, gravando o arquivo em chunks no disco em vez de carregar o vídeo inteiro em memória. O limite lógico do aplicativo é configurado pela variável de ambiente `MAX_UPLOAD_SIZE_GB`:

- Valor padrão: `20` (20GB).
- Exemplo: `MAX_UPLOAD_SIZE_GB=50` permite até 50GB no app.
- `MAX_UPLOAD_SIZE_GB=0` remove o limite lógico do app; ainda assim, o upload pode falhar por limites externos.

Extensões aceitas: `mp4`, `mov`, `mkv`, `webm`.

O limite real também depende do espaço livre em disco, do navegador, de timeouts e limites de reverse proxy, e de plataformas como Railway, Nginx ou Cloudflare quando estiverem na frente do FastAPI. Em ambiente desktop/local, configure esses componentes para permitir arquivos muito grandes e garanta espaço suficiente na pasta `data/uploads`.
