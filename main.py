from fastapi import FastAPI
from fastapi.responses import JSONResponse
import re
from scout import scout

app = FastAPI()


#Home route
@app.get("/")
def home():
	return {"message": "Welcome to the Scout Crawler API"}


# Scout route
@app.get("/scout/{cas_or_name}")
async def run_scout(cas_or_name):
	if cas_or_name is None:
		return {"error": "No input provided."}

	# identify cas or name
	cas_pattern = r'^\d{2,7}-\d{2}-\d$'
	match = re.match(cas_pattern, cas_or_name)

	if bool(match):
		response = scout(cas=cas_or_name, name=None)
	else:
		response = scout(cas=None, name=cas_or_name)

	return JSONResponse(content=response)


# Scout with excel
