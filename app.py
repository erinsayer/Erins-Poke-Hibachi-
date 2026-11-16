@app.route("/")
def home():
    return render_template_string("""<!doctype html><html><head><title>Erin's Poké & Hibachi Bowls</title>""" + STYLE + """</head><body>
<header><h1>Erin's Poké & Hibachi Bowls</h1><p>Fresh bowls made to order</p></header>
<div class="container">
<div class="notice"><strong>Delivery:</strong> Text <strong>{{phone}}</strong> for delivery.</div>

<form method="post" action="/order">

<div class="card"><h2>Poké Bowls</h2>
{% for item in poke %}
<div class="item">
<h3>{{item.name}}</h3>
<div class="description">{{item.description}}</div>
<div class="price">${{"%.2f"|format(item.price)}}</div>

<label>Quantity</label>
<select name="qty_{{item.name|replace(' ','_')}}">
{% for n in range(0,11) %}<option value="{{n}}">{{n}}</option>{% endfor %}
</select>

<label style="display:flex;align-items:center;gap:8px;font-weight:700;margin-top:12px;">
<input type="checkbox" name="extra_{{item.name|replace(' ','_')}}" value="1" style="width:auto;margin:0;">
Add another protein +$5
</label>

</div>
{% endfor %}
</div>

<div class="card"><h2>Hibachi Bowls</h2>
{% for item in hibachi %}
<div class="item">
<h3>{{item.name}}</h3>
<div class="description">{{item.description}}</div>
<div class="price">${{"%.2f"|format(item.price)}}</div>

<label>Quantity</label>
<select name="qty_{{item.name|replace(' ','_')}}">
{% for n in range(0,11) %}<option value="{{n}}">{{n}}</option>{% endfor %}
</select>

<label style="display:flex;align-items:center;gap:8px;font-weight:700;margin-top:12px;">
<input type="checkbox" name="extra_{{item.name|replace(' ','_')}}" value="1" style="width:auto;margin:0;">
Add another protein +$5
</label>

</div>
{% endfor %}
</div>

<div class="card"><h2>Your Information</h2>
<label>Customer Name</label><input name="customer_name" required>
<label>Phone Number</label><input name="phone" type="tel" required>
<label>Payment Method</label>
<select name="payment_method" required>
<option value="">Select payment method</option>
<option>Cash App</option>
<option>Venmo</option>
<option>Apple Cash</option>
<option>Cash</option>
</select>

<label>Notes / Special Instructions</label>
<textarea name="notes" rows="4"></textarea>

<div class="total">Order Total: $<span id="total">0.00</span></div>
<button type="submit">Place Order</button>
</div>
</form>

<div class="card"><h2>Payment</h2>
<p><strong>Cash App:</strong> $ErinASayer</p>
<p><strong>Venmo:</strong> @ErinASayer</p>
<p><strong>Apple Cash:</strong> (912) 327-0026</p>
<p><strong>Cash:</strong> Accepted</p>
</div>

<div class="card"><a class="button" href="/feedback">Feedback</a></div>

<div class="card"><a class="button" href="/owner">Owner Login</a></div>

</div>

<script>
const prices={
{% for item in poke %}
"{{item.name|replace(' ','_')}}":{{item.price}},
{% endfor %}
{% for item in hibachi %}
"{{item.name|replace(' ','_')}}":{{item.price}}{% if not loop.last %},{% endif %}
{% endfor %}
};

function updateTotal(){
    let t=0;

    for(const [n,p] of Object.entries(prices)){
        const qty=document.querySelector('[name="qty_'+n+'"]');
        const extra=document.querySelector('[name="extra_'+n+'"]');

        if(qty){
            t += Number(qty.value) * p;

            if(extra && extra.checked && Number(qty.value) > 0){
                t += 5;
            }
        }
    }

    document.getElementById("total").textContent=t.toFixed(2);
}

document.querySelectorAll("select,input[type=checkbox]").forEach(e=>{
    e.addEventListener("change",updateTotal);
});

updateTotal();
</script>

</body></html>""", poke=MENU["Poké Bowls"], hibachi=MENU["Hibachi Bowls"], phone=PHONE)
