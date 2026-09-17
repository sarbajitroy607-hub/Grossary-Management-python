const EMOJIS = { rice:"🍚", wheat:"🌾", flour:"🍞", oil:"🫙", daal:"🫘", soap:"🧼", surf:"🧴" };
function getEmoji(name) { return EMOJIS[name.toLowerCase()] || "🛒"; }

let currentItem = null;

async function loadItems() {
  const res = await fetch("/api/items");
  const items = await res.json();
  const grid = document.getElementById("items-grid");
  grid.innerHTML = "";
  items.forEach(item => {
    const stockLabel = item.stock === 0 ? "Out of Stock" : item.stock <= 3 ? `Low Stock (${item.stock})` : `In Stock (${item.stock})`;
    const badgeCls = item.stock === 0 ? "badge-out" : item.stock <= 3 ? "badge-low" : "badge-ok";
    const card = document.createElement("div");
    card.className = "item-card" + (item.stock === 0 ? " out-of-stock" : "");
    card.innerHTML = `
      <div class="item-emoji">${getEmoji(item.name)}</div>
      <div class="item-name">${item.name.charAt(0).toUpperCase()+item.name.slice(1)}</div>
      <div class="item-price">Rs. ${item.price}</div>
      <span class="stock-badge ${badgeCls}">${stockLabel}</span>
    `;
    if (item.stock > 0) {
      card.addEventListener("click", () => openModal(item));
    }
    grid.appendChild(card);
  });
}

function openModal(item) {
  currentItem = item;
  document.getElementById("modal-item-name").textContent = item.name.charAt(0).toUpperCase()+item.name.slice(1);
  document.getElementById("modal-item-info").textContent = `Price: Rs. ${item.price} | Available: ${item.stock} units`;
  document.getElementById("qty-input").value = 1;
  document.getElementById("qty-input").max = item.stock;
  document.getElementById("modal-overlay").classList.remove("hidden");
}
function closeModal() { document.getElementById("modal-overlay").classList.add("hidden"); currentItem = null; }

document.getElementById("modal-cancel").addEventListener("click", closeModal);
document.getElementById("modal-overlay").addEventListener("click", e => { if(e.target===document.getElementById("modal-overlay")) closeModal(); });

document.getElementById("qty-dec").addEventListener("click", () => {
  const inp = document.getElementById("qty-input");
  if (parseInt(inp.value) > 1) inp.value = parseInt(inp.value) - 1;
});
document.getElementById("qty-inc").addEventListener("click", () => {
  const inp = document.getElementById("qty-input");
  const max = currentItem ? currentItem.stock : 999;
  if (parseInt(inp.value) < max) inp.value = parseInt(inp.value) + 1;
});

document.getElementById("modal-add").addEventListener("click", async () => {
  if (!currentItem) return;
  const qty = parseInt(document.getElementById("qty-input").value);
  const res = await fetch("/api/cart/add", {
    method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({item: currentItem.name, qty})
  });
  const data = await res.json();
  closeModal();
  showToast(data.message, data.success ? "success" : "error");
  if (data.success) { loadItems(); loadCart(); }
});

async function loadCart() {
  const res = await fetch("/api/cart");
  const data = await res.json();
  const count = data.items.reduce((s,i)=>s+i.qty, 0);
  document.getElementById("cart-count").textContent = count;
  const cartItems = document.getElementById("cart-items");
  const cartFooter = document.getElementById("cart-footer");
  if (data.items.length === 0) {
    cartItems.innerHTML = `<div class="empty-cart"><div class="empty-icon">🛒</div><p>Your cart is empty</p></div>`;
    cartFooter.classList.add("hidden");
  } else {
    cartFooter.classList.remove("hidden");
    cartItems.innerHTML = data.items.map(i => `
      <div class="cart-item-row">
        <div>
          <div class="cart-item-name">${i.name.charAt(0).toUpperCase()+i.name.slice(1)}</div>
          <div class="cart-item-details">× ${i.qty} &nbsp;·&nbsp; Rs. ${i.total}</div>
        </div>
        <button class="remove-btn" data-item="${i.name}" data-qty="${i.qty}">Remove</button>
      </div>
    `).join("");
    document.getElementById("cart-total-amount").textContent = "Rs. " + data.grand_total;
    cartItems.querySelectorAll(".remove-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        const r = await fetch("/api/cart/remove", {
          method:"POST", headers:{"Content-Type":"application/json"},
          body: JSON.stringify({item: btn.dataset.item, qty: parseInt(btn.dataset.qty)})
        });
        const d = await r.json();
        showToast(d.message, d.success?"success":"error");
        if(d.success){ loadItems(); loadCart(); }
      });
    });
  }
}

document.getElementById("cart-toggle-btn").addEventListener("click", () => {
  document.getElementById("cart-panel").classList.toggle("hidden");
});
document.getElementById("cart-close-btn").addEventListener("click", () => {
  document.getElementById("cart-panel").classList.add("hidden");
});

document.getElementById("clear-cart-btn").addEventListener("click", async () => {
  await fetch("/api/cart/clear", {method:"POST"});
  showToast("Cart cleared.", "success");
  loadItems(); loadCart();
});

document.getElementById("checkout-btn").addEventListener("click", async () => {
  const res = await fetch("/api/checkout", {method:"POST"});
  const data = await res.json();
  if (data.success) {
    const receiptItems = document.getElementById("receipt-items");
    receiptItems.innerHTML = data.receipt.map(i=>`
      <div class="receipt-row">
        <span>${i.name.charAt(0).toUpperCase()+i.name.slice(1)} × ${i.qty}</span>
        <span>Rs. ${i.total}</span>
      </div>
    `).join("");
    document.getElementById("receipt-grand-total").textContent = "Rs. " + data.grand_total;
    document.getElementById("receipt-overlay").classList.remove("hidden");
    document.getElementById("cart-panel").classList.add("hidden");
    loadItems(); loadCart();
  } else {
    showToast(data.message, "error");
  }
});
document.getElementById("receipt-close").addEventListener("click", () => {
  document.getElementById("receipt-overlay").classList.add("hidden");
});

function showToast(msg, type="success") {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast " + type + " show";
  setTimeout(() => t.classList.remove("show"), 3000);
}

loadItems();
loadCart();
