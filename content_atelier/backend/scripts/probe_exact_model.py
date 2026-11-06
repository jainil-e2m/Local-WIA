"""Read the exact OpenRouter public route; no credentials or inference requests."""
import argparse
import json
from pathlib import Path

import httpx


def probe(model, output):
    root=Path(output)
    root.mkdir(parents=True,exist_ok=True)
    url=f"https://openrouter.ai/api/v1/models/{model}/endpoints"
    with httpx.Client(timeout=60) as client:
        response=client.get(url)
        try:
            data=response.json()
        except ValueError:
            data={"unparsed_body":response.text[:2000]}
        record={"url":url,"status":response.status_code,"response":data}
        (root/"public-route.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
        catalog=data.get("data",{})
        summary={"requested_model":model,"status":response.status_code,"advertised_id":catalog.get("id"),
            "exact_route_found":response.status_code==200 and catalog.get("id")==model and bool(catalog.get("endpoints")),
            "endpoints":[{k:e.get(k) for k in ("provider_name","context_length","max_prompt_tokens",
                "max_completion_tokens","supported_parameters","pricing")} for e in catalog.get("endpoints",[])]}
        if not summary["exact_route_found"]:
            summary["error"]=data.get("error")
            all_models=client.get("https://openrouter.ai/api/v1/models")
            all_models.raise_for_status()
            models=all_models.json()["data"]
            summary["exact_id_in_models_catalog"]=any(m["id"]==model for m in models)
            summary["related_advertised_ids"]=[m["id"] for m in models if m["id"].startswith("openai/gpt-6")]
        (root/"model-check.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
        return summary


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    print(json.dumps(probe(args.model,args.output),indent=2))
