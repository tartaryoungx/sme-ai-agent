from fastapi import APIRouter, Request ,  status , BackgroundTasks

router = APIRouter(prefix="/webhook" , tags=["webhook"])

@router.post("/line")
async def line_webhook(request: Request , background_tasks : BackgroundTasks):

    body = await request.body()
    signature = request.headers.get("X-Line-Signature")

    #todo ai engineer implemnent ai agent to process the webhook data and perform necessary actions in the background

    return {"status" : "success"}

