function showToast(msg, type="success") {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast " + type + " show";
  setTimeout(() => t.classList.remove("show"), 3500);
}

// LOGIN
document.getElementById("login-btn").addEventListener("click", async () => {
  const email = document.getElementById("admin-email").value.trim();
  const password = document.getElementById("admin-password").value.trim();
  const res = await fetch("/api/admin/login", {
    method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({email, password})
  });
  const data = await res.json();
  if (data.success) {
    document.getElementById("login-screen").classList.add("hidden");
    document.getElementById("admin-panel").classList.remove("hidden");
    loadInventory();
  } else {
    showToast(data.message || "Login failed", "error");
  }
});
document.getElementById("admin-password").addEventListener("keydown", e => {
  if(e.key==="Enter") document.getElementById("login-btn").click();
});

// LOGOUT
document.getElementById("logout-btn").addEventListener("click", async () => {
  await fetch("/api/admin/logout", {method:"POST"});
  document.getElementById("admin-panel").classList.add("hidden");
  document.getElementById("login-screen").classList.remove("hidden");
});

// TABS
document.querySelectorAll(".admin-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".admin-tab").forEach(t=>t.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p=>p.classList.add("hidden"));
    tab.classList.add("active");
    document.getElementById("tab-"+tab.dataset.tab).classList.remove("hidden");
    if(tab.dataset.tab==="inventory") loadInventory();
  });
});

// INVENTORY
async function loadInventory() {
  const res = await fetch("/api/items");
  const items = await res.json();
  const tbody = document.getElementById("inventory-body");
  tbody.innerHTML = items.map(i => {
    const statusText = i.stock === 0 ? "Out of Stock" : i.stock <= 3 ? "Low Stock" : "In Stock";
    const statusCls = i.stock === 0 ? "badge-out" : i.stock <= 3 ? "badge-low" : "badge-ok";
    return `
    <tr>
      <td><strong>${i.name.charAt(0).toUpperCase()+i.name.slice(1)}</strong></td>
      <td>Rs. ${i.price}</td>
      <td>${i.stock}</td>
      <td><span class="stock-badge ${statusCls}">${statusText}</span></td>
    </tr>`;
  }).join("");
}

document.getElementById("refresh-btn").addEventListener("click", loadInventory);

// UPDATE STOCK
document.getElementById("update-stock-btn").addEventListener("click", async () => {
  const item = document.getElementById("stock-item").value.trim();
  const qty = document.getElementById("stock-qty").value;
  if(!item || qty==="") { showToast("Please fill all fields", "error"); return; }
  const res = await fetch("/api/admin/stock", {
    method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({item, qty: parseInt(qty)})
  });
  const data = await res.json();
  showToast(data.message, data.success?"success":"error");
  if(data.success){ document.getElementById("stock-item").value=""; document.getElementById("stock-qty").value=""; }
});

// ADD ITEM
document.getElementById("add-item-btn").addEventListener("click", async () => {
  const item = document.getElementById("new-item-name").value.trim();
  const qty = document.getElementById("new-item-qty").value;
  const price = document.getElementById("new-item-price").value;
  if(!item || qty==="" || price==="") { showToast("Please fill all fields", "error"); return; }
  const res = await fetch("/api/admin/add_item", {
    method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({item, qty: parseInt(qty), price: parseFloat(price)})
  });
  const data = await res.json();
  showToast(data.message, data.success?"success":"error");
  if(data.success){
    document.getElementById("new-item-name").value="";
    document.getElementById("new-item-qty").value="";
    document.getElementById("new-item-price").value="";
  }
});
