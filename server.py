import json
import math
import os
import random
import socket
import time
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="EssentialLink API - Multi-Rider & Proximity Dispatch")

# Enable CORS for cross-device access (laptop <-> mobile)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = os.path.join(os.path.dirname(__file__), "database.json")

def get_local_ip() -> str:
    """Detect LAN IP so mobile devices on the same Wi-Fi can connect."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great circle distance between two points in kilometers."""
    R = 6371.0 # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

# Comprehensive City & Neighborhood Coordinates Dictionary
CITY_COORDINATES = {
    # Pune & Maharashtra Areas
    "aissms": (18.5308, 73.8647),
    "pune station": (18.5289, 73.8744),
    "pune": (18.5204, 73.8567),
    "shivajinagar": (18.5314, 73.8446),
    "kothrud": (18.5074, 73.8077),
    "deccan": (18.5167, 73.8417),
    "viman nagar": (18.5679, 73.9143),
    "hadapsar": (18.5089, 73.9259),
    "hinjewadi": (18.5913, 73.7389),
    "wakad": (18.5987, 73.7688),
    "baner": (18.5590, 73.7868),
    "camp": (18.5167, 73.8794),
    "swargate": (18.5018, 73.8586),
    "pimpri": (18.6279, 73.8009),
    "chinchwad": (18.6298, 73.7997),
    "katraj": (18.4575, 73.8677),
    "kalyani nagar": (18.5463, 73.9034),
    "magarpatta": (18.5146, 73.9272),
    
    # Mumbai Areas
    "mumbai": (19.0760, 72.8777),
    "bandra": (19.0596, 72.8295),
    "andheri": (19.1136, 72.8697),
    "dadar": (19.0178, 72.8478),
    "thane": (19.2183, 72.9781),
    "navi mumbai": (19.0330, 73.0297),
    
    # Delhi & NCR Areas
    "delhi": (28.6139, 77.2090),
    "new delhi": (28.6139, 77.2090),
    "connaught place": (28.6315, 77.2167),
    "lajpat nagar": (28.5677, 77.2433),
    "saket": (28.5244, 77.2155),
    "south ext": (28.5700, 77.2200),
    "dwarka": (28.5921, 77.0460),
    "noida": (28.5355, 77.3910),
    "gurugram": (28.4595, 77.0266),
    
    # Other Major Metros
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "hyderabad": (17.3850, 78.4867),
    "chennai": (13.0827, 80.2707),
    "kolkata": (22.5726, 88.3639)
}

def resolve_location_coords(location_str: str, address_str: str = "") -> tuple:
    """Intelligently map an address or area name to real-world coordinates with micro-jitter."""
    combined = f"{location_str} {address_str}".lower().strip()
    
    for key, (lat, lng) in CITY_COORDINATES.items():
        if key in combined:
            jitter_lat = (random.random() - 0.5) * 0.006
            jitter_lng = (random.random() - 0.5) * 0.006
            return round(lat + jitter_lat, 5), round(lng + jitter_lng, 5)
            
    # Default fallback to Pune Station / AISSMS zone
    jitter_lat = (random.random() - 0.5) * 0.008
    jitter_lng = (random.random() - 0.5) * 0.008
    return round(18.5308 + jitter_lat, 5), round(73.8647 + jitter_lng, 5)

# Seed dataset with diverse fleet covering Pune, Mumbai & Delhi
DEFAULT_DATA = {
    "requests": [
        {
            "id": "REQ-104921",
            "receiverName": "AISSMS Student Food Bank",
            "receiverMobile": "+91 98220 34567",
            "reason": "Food shortage",
            "category": "Food & Nutrition",
            "item": "Hot Cooked Meals",
            "quantity": 45,
            "address": "Near AISSMS COE Campus, Kennedy Road",
            "location": "Pune",
            "lat": 18.5308,
            "lng": 73.8647,
            "deliveryTime": "Today before 7:30 PM",
            "notes": "Large batch required for relief camp evening distribution.",
            "status": "Pending",
            "createdAt": int(time.time() * 1000) - 3600000
        },
        {
            "id": "REQ-104880",
            "receiverName": "Shivajinagar Clinic",
            "receiverMobile": "+91 98111 55667",
            "reason": "Medical emergency",
            "category": "Medical Supplies",
            "item": "First-aid & Bandages Kit",
            "quantity": 10,
            "address": "Opposite Bus Stand, Shivajinagar",
            "location": "Pune",
            "lat": 18.5314,
            "lng": 73.8446,
            "deliveryTime": "Immediate",
            "notes": "Urgent emergency kit requirement for walk-in patients.",
            "status": "Pending",
            "createdAt": int(time.time() * 1000) - 7200000
        }
    ],
    "orders": [
        {
            "id": "EL-894120",
            "requestId": "REQ-104921",
            "item": "Hot Cooked Meals",
            "category": "Food & Nutrition",
            "quantity": 35,
            "receiverName": "AISSMS Student Food Bank",
            "receiverMobile": "+91 98220 34567",
            "deliveryAddress": "Near AISSMS COE Campus, Kennedy Road",
            "deliveryLocation": "Pune",
            "receiverLat": 18.5308,
            "receiverLng": 73.8647,
            "donorName": "Annapurna Kitchen",
            "donorPhone": "+91 98230 44556",
            "pickupAddress": "FC Road, Deccan Gymkhana",
            "donorLat": 18.5180,
            "donorLng": 73.8420,
            "pickupNotes": "Cartons packed in clean thermal carriers.",
            "expiry": 60,
            "expiresAt": int(time.time() * 1000) + 3600 * 1000,
            "assignedAt": int(time.time() * 1000) - 300000, # 5 mins ago
            "status": "In Transit",
            "progress": 65,
            "isDelayed": False,
            "delayReason": "",
            "assignedRiders": [
                {
                    "riderId": "R-PNE-101",
                    "riderName": "Rahul Shinde",
                    "mobile": "+91 98220 11223",
                    "vehicle": "Motorcycle",
                    "assignedUnits": 20,
                    "distanceKm": 1.4,
                    "status": "In Transit",
                    "lat": 18.5240,
                    "lng": 73.8510
                },
                {
                    "riderId": "R-PNE-102",
                    "riderName": "Priya Kulkarni",
                    "mobile": "+91 98229 88776",
                    "vehicle": "Electric Scooter",
                    "assignedUnits": 15,
                    "distanceKm": 2.1,
                    "status": "In Transit",
                    "lat": 18.5260,
                    "lng": 73.8490
                }
            ],
            "riderId": "R-PNE-101",
            "riderName": "Rahul Shinde & Priya Kulkarni (Split: 2 Riders)",
            "riderMobile": "+91 98220 11223",
            "riderLat": 18.5240,
            "riderLng": 73.8510,
            "createdAt": int(time.time() * 1000) - 1800000,
            "auditLog": [
                "Order created. High quantity (35 units) split across 2 nearest riders: Rahul Shinde (20 units) & Priya Kulkarni (15 units)."
            ]
        }
    ],
    "riders": [
        # Pune Fleet
        {
            "id": "R-PNE-101",
            "name": "Rahul Shinde",
            "mobile": "+91 98220 11223",
            "vehicle": "Motorcycle",
            "capacity": 20,
            "assigned": 1,
            "location": "Pune Station / AISSMS Hub",
            "lat": 18.5300,
            "lng": 73.8640,
            "available": True,
            "stars": 28
        },
        {
            "id": "R-PNE-102",
            "name": "Priya Kulkarni",
            "mobile": "+91 98229 88776",
            "vehicle": "Electric Scooter",
            "capacity": 15,
            "assigned": 1,
            "location": "Shivajinagar Hub",
            "lat": 18.5320,
            "lng": 73.8450,
            "available": True,
            "stars": 34
        },
        {
            "id": "R-PNE-103",
            "name": "Tanmay Joshi",
            "mobile": "+91 98900 45678",
            "vehicle": "Delivery Van",
            "capacity": 45,
            "assigned": 0,
            "location": "Swargate / Deccan Hub",
            "lat": 18.5080,
            "lng": 73.8550,
            "available": True,
            "stars": 42
        },
        {
            "id": "R-PNE-104",
            "name": "Sneha Deshmukh",
            "mobile": "+91 97654 32109",
            "vehicle": "Bicycle Express",
            "capacity": 10,
            "assigned": 0,
            "location": "Kothrud / Deccan Hub",
            "lat": 18.5100,
            "lng": 73.8180,
            "available": True,
            "stars": 19
        },
        # Mumbai Fleet
        {
            "id": "R-MUM-201",
            "name": "Sameer Merchant",
            "mobile": "+91 98190 33445",
            "vehicle": "Motorcycle",
            "capacity": 20,
            "assigned": 0,
            "location": "Dadar Central Hub",
            "lat": 19.0178,
            "lng": 72.8478,
            "available": True,
            "stars": 31
        },
        # Delhi Fleet
        {
            "id": "R-DEL-301",
            "name": "Vikram Singh",
            "mobile": "+91 98102 99384",
            "vehicle": "Motorcycle",
            "capacity": 20,
            "assigned": 0,
            "location": "Connaught Place Hub",
            "lat": 28.6315,
            "lng": 77.2167,
            "available": True,
            "stars": 25
        }
    ]
}

def load_db() -> Dict[str, Any]:
    if not os.path.exists(DB_FILE):
        save_db(DEFAULT_DATA)
        return DEFAULT_DATA
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure riders list has proper initial fleet if empty
            if not data.get("riders"):
                data["riders"] = DEFAULT_DATA["riders"]
                save_db(data)
            return data
    except Exception:
        return DEFAULT_DATA

def save_db(data: Dict[str, Any]):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Pydantic Request Models
class ReceiverRequestModel(BaseModel):
    receiverName: str
    receiverMobile: str
    reason: str
    category: str
    item: str
    quantity: int
    address: str
    location: Optional[str] = ""
    lat: Optional[float] = None
    lng: Optional[float] = None
    deliveryTime: Optional[str] = "Urgent / ASAP"
    notes: Optional[str] = ""

class DonateRequestModel(BaseModel):
    requestId: str
    donorName: str
    donorPhone: str
    pickupAddress: str
    expiry: Optional[int] = 60
    pickupNotes: Optional[str] = ""
    donorLat: Optional[float] = None
    donorLng: Optional[float] = None

class RiderRegisterModel(BaseModel):
    name: str
    mobile: str
    vehicle: str
    capacity: int
    location: Optional[str] = "Pune Station / AISSMS Hub"
    lat: Optional[float] = None
    lng: Optional[float] = None

class UpdateOrderModel(BaseModel):
    status: str
    progress: int
    riderLat: Optional[float] = None
    riderLng: Optional[float] = None

# API Routes
@app.get("/api/info")
def get_info():
    """Returns local network connection info for mobile access."""
    local_ip = get_local_ip()
    return {
        "local_ip": local_ip,
        "port": 8000,
        "mobile_url": f"http://{local_ip}:8000",
        "laptop_url": "http://localhost:8000",
        "timestamp": int(time.time() * 1000)
    }

@app.get("/api/geocode")
def geocode_preview(q: str):
    """Resolve location text into geographic coordinates."""
    lat, lng = resolve_location_coords(q)
    return {"query": q, "lat": lat, "lng": lng}

@app.get("/api/state")
def get_state():
    """Returns the shared real-time state for all connected devices."""
    db = load_db()
    total_reqs = len(db.get("requests", []))
    donated_reqs = len([r for r in db.get("requests", []) if r.get("status") == "Donated"])
    active_deliveries = len([o for o in db.get("orders", []) if o.get("status") not in ["Delivered", "Expired"]])
    available_riders = len([r for r in db.get("riders", []) if r.get("available")])

    return {
        "requests": db.get("requests", []),
        "orders": db.get("orders", []),
        "riders": db.get("riders", []),
        "stats": {
            "totalRequests": total_reqs,
            "donatedRequests": donated_reqs,
            "activeDeliveries": active_deliveries,
            "availableRiders": available_riders
        },
        "server_ip": get_local_ip()
    }

@app.post("/api/requests")
def create_request(payload: ReceiverRequestModel):
    db = load_db()
    req_id = "REQ-" + str(int(time.time() * 1000))[-6:]
    
    # Resolve real coordinates from location & address
    if payload.lat is not None and payload.lng is not None and payload.lat != 0:
        c_lat, c_lng = payload.lat, payload.lng
    else:
        c_lat, c_lng = resolve_location_coords(payload.location or "", payload.address or "")
        
    new_req = {
        "id": req_id,
        "receiverName": payload.receiverName,
        "receiverMobile": payload.receiverMobile,
        "reason": payload.reason,
        "category": payload.category,
        "item": payload.item,
        "quantity": payload.quantity,
        "address": payload.address,
        "location": payload.location or "Pune",
        "lat": c_lat,
        "lng": c_lng,
        "deliveryTime": payload.deliveryTime or "As soon as possible",
        "notes": payload.notes or "",
        "status": "Pending",
        "createdAt": int(time.time() * 1000)
    }
    db["requests"].insert(0, new_req)
    save_db(db)
    return {"success": True, "request": new_req}

@app.post("/api/donate")
def confirm_donation(payload: DonateRequestModel):
    """
    Fulfills donation with:
    1. Proximity-based nearest rider prioritization (Haversine distance).
    2. Multi-rider splitting if quantity exceeds a single rider's capacity.
    3. Accurate coordinates for pickup and drop.
    """
    db = load_db()
    
    # 1. Find the target request
    target_req = None
    for r in db["requests"]:
        if r["id"] == payload.requestId:
            target_req = r
            break

    if not target_req:
        raise HTTPException(status_code=404, detail="Request not found")

    # 2. Resolve donor pickup coordinates
    if payload.donorLat is not None and payload.donorLng is not None and payload.donorLat != 0:
        p_lat, p_lng = payload.donorLat, payload.donorLng
    else:
        p_lat, p_lng = resolve_location_coords(payload.pickupAddress, target_req.get("location", ""))

    receiver_lat = target_req.get("lat") or 18.5308
    receiver_lng = target_req.get("lng") or 73.8647
    total_quantity = target_req.get("quantity", 10)

    # 3. Calculate distance from EVERY available rider to the pickup point
    available_riders = []
    for rider in db.get("riders", []):
        if rider.get("available") and rider.get("assigned", 0) < rider.get("capacity", 20):
            r_lat = rider.get("lat", p_lat)
            r_lng = rider.get("lng", p_lng)
            dist_km = haversine(r_lat, r_lng, p_lat, p_lng)
            available_riders.append({
                "rider": rider,
                "dist_km": dist_km,
                "rem_cap": rider.get("capacity", 20) - rider.get("assigned", 0)
            })

    # Sort available riders by proximity (nearest to pickup first)
    available_riders.sort(key=lambda x: x["dist_km"])

    assigned_riders_list = []
    audit_notes = []
    remaining_to_assign = total_quantity

    if available_riders:
        # Multi-rider splitting algorithm based on capacity & proximity
        for item in available_riders:
            if remaining_to_assign <= 0:
                break
            r = item["rider"]
            rem_cap = item["rem_cap"]
            
            # Allocation for this rider
            take_units = min(rem_cap, remaining_to_assign)
            if take_units <= 0:
                continue

            r["assigned"] = r.get("assigned", 0) + 1
            if r["assigned"] >= r.get("capacity", 20):
                r["available"] = False

            assigned_riders_list.append({
                "riderId": r["id"],
                "riderName": r["name"],
                "mobile": r["mobile"],
                "vehicle": r["vehicle"],
                "assignedUnits": take_units,
                "distanceKm": item["dist_km"],
                "status": "Assigned",
                "lat": r.get("lat", p_lat),
                "lng": r.get("lng", p_lng)
            })
            remaining_to_assign -= take_units

        if len(assigned_riders_list) > 1:
            split_summary = ", ".join([f"{a['riderName']} ({a['assignedUnits']} units - {a['distanceKm']}km)" for a in assigned_riders_list])
            audit_notes.append(f"⚡ High Volume Order ({total_quantity} units) split across {len(assigned_riders_list)} nearest riders: {split_summary}.")
        else:
            primary_r = assigned_riders_list[0]
            audit_notes.append(f"Nearest rider {primary_r['riderName']} ({primary_r['distanceKm']} km away) assigned for {primary_r['assignedUnits']} units.")
    else:
        audit_notes.append("No active riders currently available nearby; queued for next available volunteer.")

    order_id = "EL-" + str(int(time.time() * 1000))[-6:]
    expires_at = int(time.time() * 1000) + (payload.expiry * 60 * 1000) if payload.expiry > 0 else None

    # Primary display names
    if assigned_riders_list:
        if len(assigned_riders_list) == 1:
            primary_name = assigned_riders_list[0]["riderName"]
            primary_mobile = assigned_riders_list[0]["mobile"]
            primary_lat = assigned_riders_list[0]["lat"]
            primary_lng = assigned_riders_list[0]["lng"]
        else:
            primary_name = f"{assigned_riders_list[0]['riderName']} (+{len(assigned_riders_list)-1} other riders)"
            primary_mobile = assigned_riders_list[0]["mobile"]
            primary_lat = assigned_riders_list[0]["lat"]
            primary_lng = assigned_riders_list[0]["lng"]
    else:
        primary_name = None
        primary_mobile = None
        primary_lat = p_lat
        primary_lng = p_lng

    order = {
        "id": order_id,
        "requestId": target_req["id"],
        "item": target_req["item"],
        "category": target_req["category"],
        "quantity": total_quantity,
        "receiverName": target_req["receiverName"],
        "receiverMobile": target_req["receiverMobile"],
        "deliveryAddress": target_req["address"],
        "deliveryLocation": target_req.get("location", "Pune"),
        "receiverLat": receiver_lat,
        "receiverLng": receiver_lng,
        "donorName": payload.donorName,
        "donorPhone": payload.donorPhone,
        "pickupAddress": payload.pickupAddress,
        "donorLat": p_lat,
        "donorLng": p_lng,
        "pickupNotes": payload.pickupNotes or "",
        "expiry": payload.expiry,
        "expiresAt": expires_at,
        "assignedAt": int(time.time() * 1000),
        "riderId": assigned_riders_list[0]["riderId"] if assigned_riders_list else None,
        "riderName": primary_name,
        "riderMobile": primary_mobile,
        "riderLat": primary_lat,
        "riderLng": primary_lng,
        "assignedRiders": assigned_riders_list,
        "status": "Rider Assigned" if assigned_riders_list else "Waiting for Rider",
        "progress": 25 if assigned_riders_list else 10,
        "isDelayed": False,
        "delayReason": "",
        "createdAt": int(time.time() * 1000),
        "auditLog": audit_notes
    }

    target_req["status"] = "Donated"
    target_req["donorName"] = payload.donorName
    target_req["orderId"] = order_id

    db["orders"].insert(0, order)
    save_db(db)
    return {
        "success": True,
        "order": order,
        "rider_assigned": bool(assigned_riders_list),
        "split_count": len(assigned_riders_list)
    }

@app.post("/api/orders/{order_id}/emergency-reassign")
def emergency_reassign_rider(order_id: str):
    """
    Emergency Reassignment:
    If a rider is stuck in traffic or cannot reach within the 10-minute wait window:
    1. Marks the stuck rider as delayed.
    2. Immediately queries the fleet for the next nearest available rider.
    3. Transfers the delivery portion to the backup rider.
    4. Logs the emergency handover event.
    """
    db = load_db()
    target_order = None
    for o in db["orders"]:
        if o["id"] == order_id:
            target_order = o
            break

    if not target_order:
        raise HTTPException(status_code=404, detail="Order not found")

    pickup_lat = target_order.get("donorLat", 18.5308)
    pickup_lng = target_order.get("donorLng", 73.8647)
    previous_rider_name = target_order.get("riderName", "Assigned Courier")

    # Find previously assigned rider IDs to exclude
    already_assigned_ids = set()
    if target_order.get("assignedRiders"):
        for a in target_order["assignedRiders"]:
            already_assigned_ids.add(a.get("riderId"))
    elif target_order.get("riderId"):
        already_assigned_ids.add(target_order.get("riderId"))

    # Free the stuck rider's load count so they aren't blocked forever
    for r in db.get("riders", []):
        if r["id"] in already_assigned_ids:
            r["assigned"] = max(0, r.get("assigned", 1) - 1)
            r["available"] = True

    # Search for the nearest backup rider excluding the stuck rider
    backup_riders = []
    for r in db.get("riders", []):
        if r["id"] not in already_assigned_ids and r.get("available") and r.get("assigned", 0) < r.get("capacity", 20):
            dist = haversine(r.get("lat", pickup_lat), r.get("lng", pickup_lng), pickup_lat, pickup_lng)
            backup_riders.append({"rider": r, "dist_km": dist})

    backup_riders.sort(key=lambda x: x["dist_km"])

    if not backup_riders:
        target_order["status"] = "Rider Delayed - Searching Fleet"
        target_order["isDelayed"] = True
        target_order["delayReason"] = "Stuck in traffic (>10m wait threshold reached). Searching backup fleet."
        if not target_order.get("auditLog"):
            target_order["auditLog"] = []
        target_order["auditLog"].append(f"⚠️ 10-Minute Traffic Delay: {previous_rider_name} stuck in severe traffic. No backup rider available nearby yet.")
        save_db(db)
        return {
            "success": False,
            "message": "No backup rider immediately available nearby. Queued in priority dispatch.",
            "order": target_order
        }

    new_backup = backup_riders[0]["rider"]
    new_dist = backup_riders[0]["dist_km"]
    new_backup["assigned"] = new_backup.get("assigned", 0) + 1
    if new_backup["assigned"] >= new_backup.get("capacity", 20):
        new_backup["available"] = False

    # Update order to the new nearest backup rider
    target_order["riderId"] = new_backup["id"]
    target_order["riderName"] = new_backup["name"]
    target_order["riderMobile"] = new_backup["mobile"]
    target_order["riderLat"] = new_backup["lat"]
    target_order["riderLng"] = new_backup["lng"]
    target_order["assignedRiders"] = [
        {
            "riderId": new_backup["id"],
            "riderName": new_backup["name"],
            "mobile": new_backup["mobile"],
            "vehicle": new_backup["vehicle"],
            "assignedUnits": target_order.get("quantity", 10),
            "distanceKm": new_dist,
            "status": "Emergency Dispatched",
            "lat": new_backup["lat"],
            "lng": new_backup["lng"]
        }
    ]
    target_order["status"] = "Emergency Reassigned"
    target_order["isDelayed"] = True
    target_order["delayReason"] = f"Previous courier delayed in traffic. Emergency handover to nearest rider {new_backup['name']} ({new_dist} km away)."
    target_order["assignedAt"] = int(time.time() * 1000) # Reset wait timer for new rider

    if not target_order.get("auditLog"):
        target_order["auditLog"] = []
    target_order["auditLog"].append(
        f"🚨 10-Minute Traffic Delay Triggered: Courier {previous_rider_name} was unable to proceed due to heavy traffic. "
        f"Delivery automatically reassigned to nearest backup rider {new_backup['name']} ({new_dist} km away)."
    )

    save_db(db)
    return {
        "success": True,
        "message": f"Successfully reassigned to nearest backup rider {new_backup['name']} ({new_dist} km away).",
        "new_rider": new_backup,
        "order": target_order
    }

@app.post("/api/riders")
def register_rider(payload: RiderRegisterModel):
    db = load_db()
    rider_id = "R-" + str(int(time.time() * 1000))[-4:]
    
    # Resolve real coordinates from location
    if payload.lat is not None and payload.lng is not None and payload.lat != 0:
        r_lat, r_lng = payload.lat, payload.lng
    else:
        r_lat, r_lng = resolve_location_coords(payload.location or "Pune")
        
    new_rider = {
        "id": rider_id,
        "name": payload.name,
        "mobile": payload.mobile,
        "vehicle": payload.vehicle,
        "capacity": payload.capacity,
        "assigned": 0,
        "location": payload.location or "Pune Station / AISSMS Hub",
        "lat": r_lat,
        "lng": r_lng,
        "available": True,
        "stars": 0
    }
    db["riders"].append(new_rider)
    save_db(db)
    return {"success": True, "rider": new_rider}

@app.patch("/api/orders/{order_id}")
def update_order(order_id: str, payload: UpdateOrderModel):
    db = load_db()
    target_order = None
    for o in db["orders"]:
        if o["id"] == order_id:
            target_order = o
            break

    if not target_order:
        raise HTTPException(status_code=404, detail="Order not found")

    target_order["status"] = payload.status
    target_order["progress"] = payload.progress

    if payload.riderLat is not None:
        target_order["riderLat"] = payload.riderLat
    if payload.riderLng is not None:
        target_order["riderLng"] = payload.riderLng

    # If delivered, free up assigned capacity for ALL assigned riders on this order
    if payload.status == "Delivered":
        rider_ids_to_free = set()
        if target_order.get("assignedRiders"):
            for a in target_order["assignedRiders"]:
                rider_ids_to_free.add(a.get("riderId"))
        elif target_order.get("riderId"):
            rider_ids_to_free.add(target_order.get("riderId"))

        for rider in db.get("riders", []):
            if rider["id"] in rider_ids_to_free:
                rider["assigned"] = max(0, rider.get("assigned", 1) - 1)
                rider["available"] = True
                rider["stars"] = rider.get("stars", 0) + 5

    save_db(db)
    return {"success": True, "order": target_order}

@app.post("/api/admin/approve/{request_id}")
def admin_approve(request_id: str):
    db = load_db()
    for r in db["requests"]:
        if r["id"] == request_id:
            r["status"] = "Approved & Priority"
            save_db(db)
            return {"success": True, "request": r}
    raise HTTPException(status_code=404, detail="Request not found")

@app.post("/api/admin/reject/{request_id}")
def admin_reject(request_id: str):
    db = load_db()
    for r in db["requests"]:
        if r["id"] == request_id:
            r["status"] = "Rejected by Admin"
            save_db(db)
            return {"success": True, "request": r}
    raise HTTPException(status_code=404, detail="Request not found")

# Mount Static Files (Frontend UI)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

if __name__ == "__main__":
    import uvicorn
    local_ip = get_local_ip()
    print("=" * 68)
    print("  EssentialLink Intelligent Proximity & Multi-Rider Dispatch")
    print(f"  -> Laptop Access:  http://localhost:8000")
    print(f"  -> Mobile Access:  http://{local_ip}:8000")
    print("=" * 68)
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
