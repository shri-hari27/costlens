import azure.functions as func
import logging
import json

from shared_logic import write_snapshot

app = func.FunctionApp()


@app.timer_trigger(schedule="0 0 6 * * *", arg_name="mytimer", run_on_startup=False)
def daily_snapshot(mytimer: func.TimerRequest) -> None:
    """Runs once daily at 06:00 UTC — pulls Cost Management + Resource Graph data, writes snapshot."""
    logging.info("Timer trigger fired: starting daily cost snapshot")
    try:
        cost_data, waste_data = write_snapshot()
        logging.info(f"Daily snapshot complete. Total cost: ${cost_data['totalCost']}, waste findings: {waste_data['totalFindings']}")
    except Exception as e:
        logging.error(f"Daily snapshot failed: {e}")
        raise


@app.route(route="refresh", methods=["POST", "GET"], auth_level=func.AuthLevel.ANONYMOUS)
def refresh_now(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP-triggered manual refresh — same logic as the timer, callable on demand from the dashboard."""
    logging.info("HTTP trigger fired: manual refresh requested")
    try:
        cost_data, waste_data = write_snapshot()
        result = {
            "status": "success",
            "totalCost": cost_data["totalCost"],
            "wasteFindings": waste_data["totalFindings"],
            "snapshotDate": cost_data["snapshotDate"],
        }
        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as e:
        logging.error(f"Manual refresh failed: {e}")
        return func.HttpResponse(
            json.dumps({"status": "error", "message": str(e)}),
            mimetype="application/json",
            status_code=500,
        )
