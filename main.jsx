import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

const api = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

function App() {
  const [plan, setPlan] = useState(null);
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);

  async function submit(event) {
    event.preventDefault();
    const fields = new FormData(event.currentTarget);
    setPending(true);
    setPlan(null);
    setError('');
    try {
      const response = await fetch(`${api}/api/plans`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          height_cm: Number(fields.get('height')),
          weight_kg: Number(fields.get('weight')),
          diet: fields.get('diet'),
          days: Number(fields.get('days')),
        }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Unable to create a plan.');
      setPlan(result);
    } catch (failure) {
      setError(failure instanceof SyntaxError || failure instanceof TypeError
        ? 'Could not reach the planner. Try again in a moment.' : failure.message);
    } finally {
      setPending(false);
    }
  }

  return <main>
    <header>
      <p className="brand">LAID / MEAL PLANNER</p>
      <h1>What’s for dinner?</h1>
      <p>And breakfast. And lunch. Pick a dietary preference and get a few days of ideas.</p>
    </header>
    <form onSubmit={submit}>
      <h2>Your preferences</h2>
      <div className="fields">
        <label>Height (cm)<input name="height" type="number" min="80" max="250" step="0.1" defaultValue="175" required /></label>
        <label>Weight (kg)<input name="weight" type="number" min="20" max="350" step="0.1" defaultValue="70" required /></label>
        <label>Diet<select name="diet" defaultValue="vegetarian">
          <option value="omnivore">Omnivore</option><option value="vegetarian">Vegetarian</option><option value="vegan">Vegan</option>
        </select></label>
        <label>Days<input name="days" type="number" min="1" max="7" defaultValue="3" required /></label>
      </div>
      <p className="hint">For adults 20+. Height and weight are used to calculate BMI, separately from the menu.</p>
      <button disabled={pending}>{pending ? 'Planning…' : 'Build my meal plan'}</button>
      {error && <p role="alert">{error}</p>}
    </form>
    {plan && <section aria-live="polite">
      <div className="results">
        <h2>Your {plan.diet} meal plan</h2>
        <span>BMI estimate · {plan.bmi}</span>
      </div>
      <p className="hint">BMI is a screening measure. These are meal ideas without prescribed portions or calorie targets.</p>
      <div className="cards">
        {plan.days.map((day, index) => <article key={index}>
          <h3>Day {index + 1}</h3>
          <dl>{Object.entries(day).map(([meal, title]) => <React.Fragment key={meal}>
            <dt>{meal}</dt><dd>{title}</dd>
          </React.Fragment>)}</dl>
        </article>)}
      </div>
      {plan.groceries?.length > 0 && <fieldset style={{ marginTop: '1.5rem', borderRadius: '12px' }}>
        <legend>Grocery checklist</legend>
        <p className="hint">Core ingredients for this plan. Check off what you already have.</p>
        <div className="fields">
          {plan.groceries.map(ingredient => <label key={ingredient}>
            <input type="checkbox" style={{ width: 'auto', marginRight: '0.5rem' }} />
            {ingredient}
          </label>)}
        </div>
      </fieldset>}
    </section>}
  </main>;
}

createRoot(document.getElementById('root')).render(<App />);
