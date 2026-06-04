from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx
import asyncio
from datetime import datetime

app = FastAPI(title="API Gateway")

SERVICES = {
    "users": "http://127.0.0.1:5001",
    "products": "http://127.0.0.1:5002",
    "orders": "http://127.0.0.1:5003"
}

SERVICE_HEALTH = {
    "users": True,
    "products": True,
    "orders": True
}

async def check_services():
    async with httpx.AsyncClient() as client:
        while True:
            for name, base_url in SERVICES.items():
                is_up = False
                
                for tentativa in range(2):
                    try:
                        response = await client.get(f"{base_url}/health", timeout=2.0)
                        if response.status_code == 200:
                            is_up = True
                            break
                    except Exception:
                        pass
                
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if is_up and not SERVICE_HEALTH[name]:
                    print(f"[{timestamp}] [RECUPERAÇÃO] Serviço '{name}' voltou a responder.")
                    SERVICE_HEALTH[name] = True
                elif not is_up and SERVICE_HEALTH[name]:
                    print(f"[{timestamp}] [FALHA CRÍTICA] Serviço '{name}' não respondeu após 2 tentativas.")
                    SERVICE_HEALTH[name] = False
            
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(check_services())

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def gateway(path: str, request: Request):
    parts = path.split("/")
    service_name = parts[0]
    
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail="Serviço não mapeado no Gateway")    
    if not SERVICE_HEALTH[service_name]:
        raise HTTPException(
            status_code=503, 
            detail=f"503 Service Unavailable: O microsserviço '{service_name}' está temporariamente fora do ar."
        )
    
    target_url = f"{SERVICES[service_name]}/{path}"
    body = await request.body()
    
    headers = dict(request.headers)
    headers.pop("host", None)
    
    async with httpx.AsyncClient() as client:
        try:

            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params
            )
            
            try:
                content = response.json()
            except:
                content = response.text
                
            return JSONResponse(status_code=response.status_code, content=content)
            
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail=f"503 Serviço indisponivel: Falha de comunicação de rede com '{service_name}'.")