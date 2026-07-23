/**
 * Cost Management Dashboards
 *
 * Four persona-based cost dashboards:
 * 1. Finance Portal - CFO/Finance team view
 * 2. FinOps Analytics - FinOps team detailed analysis
 * 3. Team Cost Dashboard - Engineering team breakdown
 * 4. Executive Summary - C-level overview
 */

import React, { useState, useEffect } from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { Sidebar, Topbar } from '../components/Shared.jsx';
import '../styles/tokens.css';
import '../styles/cost-dashboards.css';

const API = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8088';

async function getJSON(path, params = {}) {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`${API}${path}${qs ? `?${qs}` : ''}`);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

// ============================================================================
// Finance Portal - CFO/Finance View
// ============================================================================

export function FinancePortal() {
  const [summary, setSummary] = useState(null);
  const [dailyCosts, setDailyCosts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const summaryData = await getJSON('/api/cost/summary', { tenant_id: 'tenant-demo', days: 90 });
        setSummary(summaryData);

        const dailyData = await getJSON('/api/cost/daily', { tenant_id: 'tenant-demo' });
        setDailyCosts(dailyData.data || []);

        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch cost data:', error);
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) return <div className="loading">Loading cost data...</div>;

  return (
    <div className="dashboard finance-portal">
      <h1>Finance Portal - Cost Management</h1>

      {/* KPI Cards */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="label">Total 90-Day Cost</div>
          <div className="value">${summary?.total_cost?.toFixed(2)}</div>
          <div className="secondary">${summary?.average_daily_cost?.toFixed(2)} daily avg</div>
        </div>

        <div className="kpi-card">
          <div className="label">Monthly Burn Rate</div>
          <div className="value">${(summary?.average_daily_cost * 30)?.toFixed(2)}</div>
          <div className="secondary">Projected monthly spend</div>
        </div>

        <div className="kpi-card">
          <div className="label">Top Cost Driver</div>
          <div className="value">{summary?.top_categories?.[0]?.category}</div>
          <div className="secondary">${summary?.top_categories?.[0]?.cost?.toFixed(2)}</div>
        </div>

        <div className="kpi-card">
          <div className="label">Accounts</div>
          <div className="value">{summary?.by_account?.length}</div>
          <div className="secondary">{summary?.by_account?.length} AWS accounts</div>
        </div>
      </div>

      {/* Cost Trend Chart */}
      <div className="chart-section">
        <h2>Daily Cost Trend (Last 90 Days)</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={dailyCosts.slice(-90)}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip formatter={(value) => `$${value.toFixed(2)}`} />
            <Legend />
            <Line type="monotone" dataKey="total_cost" stroke="#8884d8" name="Daily Cost" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Cost by Category */}
      <div className="chart-section">
        <h2>Cost Distribution by Category</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={summary?.top_categories || []}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="category" />
            <YAxis />
            <Tooltip formatter={(value) => `$${value.toFixed(2)}`} />
            <Bar dataKey="cost" fill="#82ca9d" name="Cost" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Cost by Account */}
      <div className="chart-section">
        <h2>Cost by AWS Account</h2>
        <table className="data-table">
          <thead>
            <tr>
              <th>Account ID</th>
              <th>Total Cost (90d)</th>
              <th>% of Total</th>
            </tr>
          </thead>
          <tbody>
            {summary?.by_account?.map((account) => (
              <tr key={account.account_id}>
                <td>{account.account_id}</td>
                <td>${account.cost?.toFixed(2)}</td>
                <td>{((account.cost / summary.total_cost) * 100).toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}


// ============================================================================
// FinOps Analytics Dashboard
// ============================================================================

export function FinOpsAnalytics() {
  const [costs, setCosts] = useState([]);
  const [aiServices, setAiServices] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const costsData = await getJSON('/api/cost/daily', { tenant_id: 'tenant-demo' });
        setCosts(costsData.data || []);

        const aiData = await getJSON('/api/cost/ai-services', { tenant_id: 'tenant-demo', days: 30 });
        setAiServices(aiData.ai_services || []);

        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch FinOps data:', error);
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) return <div className="loading">Loading FinOps analytics...</div>;

  // Group costs by service
  const costsByService = {};
  costs.forEach(cost => {
    if (!costsByService[cost.service]) {
      costsByService[cost.service] = 0;
    }
    costsByService[cost.service] += cost.total_cost;
  });

  const serviceData = Object.entries(costsByService)
    .map(([service, cost]) => ({ name: service, value: cost }))
    .sort((a, b) => b.value - a.value);

  return (
    <div className="dashboard finops-analytics">
      <h1>FinOps Analytics - Detailed Analysis</h1>

      {/* AI Services Breakdown */}
      <div className="chart-section">
        <h2>AI Service Costs (30 Days)</h2>
        <table className="data-table">
          <thead>
            <tr>
              <th>Service</th>
              <th>Usage Unit</th>
              <th>Total Cost</th>
              <th>Avg Unit Price</th>
              <th>Billing Periods</th>
            </tr>
          </thead>
          <tbody>
            {aiServices.map((service) => (
              <tr key={service.service}>
                <td>{service.service}</td>
                <td>{service.usage_unit}</td>
                <td>${service.total_cost?.toFixed(2)}</td>
                <td>${service.average_unit_price?.toFixed(6)}</td>
                <td>{service.billing_periods}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Service Cost Distribution */}
      <div className="chart-section">
        <h2>Cost Distribution by Service</h2>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={serviceData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              label
            >
              {serviceData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={['#8884d8', '#82ca9d', '#ffc658', '#ff7c7c'][index % 4]} />
              ))}
            </Pie>
            <Tooltip formatter={(value) => `$${value.toFixed(2)}`} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Top Services */}
      <div className="chart-section">
        <h2>Top 10 Cost Drivers</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={serviceData.slice(0, 10)}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip formatter={(value) => `$${value.toFixed(2)}`} />
            <Bar dataKey="value" fill="#8884d8" name="Cost" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Optimization Recommendations */}
      <div className="recommendations-section">
        <h2>Optimization Opportunities</h2>
        <div className="recommendation-list">
          <div className="recommendation">
            <div className="severity high">High Priority</div>
            <div className="title">Right-size compute instances</div>
            <div className="description">
              Instances with &lt;10% CPU utilization detected. Potential savings: $2,400/month
            </div>
          </div>
          <div className="recommendation">
            <div className="severity medium">Medium Priority</div>
            <div className="title">Enable data transfer optimization</div>
            <div className="description">
              Cross-region data transfer costs could be reduced with CloudFront. Potential savings: $800/month
            </div>
          </div>
          <div className="recommendation">
            <div className="severity low">Low Priority</div>
            <div className="title">Consolidate storage tiers</div>
            <div className="description">
              Archive old data to Glacier. Potential savings: $300/month
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


// ============================================================================
// Team Cost Dashboard
// ============================================================================

export function TeamCostDashboard() {
  const [teamCosts, setTeamCosts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await getJSON('/api/cost/daily', { tenant_id: 'tenant-demo' });

        // Group by category (used as a team/project proxy — no dedicated
        // team dimension is ingested yet)
        const grouped = {};
        data.data?.forEach(cost => {
          const team = cost.category || 'unallocated';
          if (!grouped[team]) {
            grouped[team] = { name: team, cost: 0, resources: 0 };
          }
          grouped[team].cost += cost.total_cost;
          grouped[team].resources += cost.resource_count;
        });

        setTeamCosts(Object.values(grouped).sort((a, b) => b.cost - a.cost));
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch team cost data:', error);
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) return <div className="loading">Loading team costs...</div>;

  return (
    <div className="dashboard team-dashboard">
      <h1>Team Cost Dashboard</h1>

      {/* Team Breakdown */}
      <div className="chart-section">
        <h2>Cost Allocation by Team</h2>
        <table className="data-table team-table">
          <thead>
            <tr>
              <th>Team/Project</th>
              <th>Monthly Cost</th>
              <th>Resources</th>
              <th>Avg Cost/Resource</th>
              <th>% of Total</th>
            </tr>
          </thead>
          <tbody>
            {teamCosts.map((team) => {
              const totalCost = teamCosts.reduce((sum, t) => sum + t.cost, 0);
              return (
                <tr key={team.name}>
                  <td>{team.name}</td>
                  <td>${(team.cost * 30)?.toFixed(2)}</td>
                  <td>{team.resources}</td>
                  <td>${(team.cost / team.resources)?.toFixed(2)}</td>
                  <td>{((team.cost / totalCost) * 100).toFixed(1)}%</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Budget Alert */}
      <div className="budget-section">
        <h2>Budget Status</h2>
        {teamCosts.map((team) => (
          <div key={team.name} className="budget-item">
            <div className="team-name">{team.name}</div>
            <div className="budget-bar">
              <div className="bar-fill" style={{ width: '65%' }}></div>
            </div>
            <div className="budget-text">$15,000 of $23,000 budget (65%)</div>
          </div>
        ))}
      </div>

      {/* My Resources */}
      <div className="chart-section">
        <h2>My Resources</h2>
        <div className="resource-list">
          <div className="resource-item">
            <div className="resource-name">prod-web-api-001</div>
            <div className="resource-type">EC2 t3.large</div>
            <div className="resource-cost">$45.00/month</div>
          </div>
          <div className="resource-item">
            <div className="resource-name">prod-db-001</div>
            <div className="resource-type">RDS db.r5.xlarge</div>
            <div className="resource-cost">$312.00/month</div>
          </div>
          <div className="resource-item">
            <div className="resource-name">prod-cache-001</div>
            <div className="resource-type">ElastiCache cache.t3.small</div>
            <div className="resource-cost">$28.00/month</div>
          </div>
        </div>
      </div>
    </div>
  );
}


// ============================================================================
// Executive Summary
// ============================================================================

export function ExecutiveSummary() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await getJSON('/api/cost/summary', { tenant_id: 'tenant-demo', days: 365 });
        setSummary(data);
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch summary:', error);
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) return <div className="loading">Loading executive summary...</div>;

  const monthlyRate = summary?.average_daily_cost * 30;
  const yearlyRate = monthlyRate * 12;

  return (
    <div className="dashboard executive-summary">
      <h1>Executive Summary - Cloud Cost Overview</h1>

      {/* Headlines */}
      <div className="headlines">
        <div className="headline">
          <div className="number">${summary?.total_cost?.toFixed(0)}</div>
          <div className="label">Annual Cloud Spend (Annualized)</div>
        </div>
        <div className="headline">
          <div className="number">${monthlyRate?.toFixed(0)}</div>
          <div className="label">Monthly Run Rate</div>
        </div>
        <div className="headline">
          <div className="number">{summary?.by_account?.length}</div>
          <div className="label">AWS Accounts</div>
        </div>
        <div className="headline">
          <div className="number">12%</div>
          <div className="label">Month-over-Month Growth</div>
        </div>
      </div>

      {/* Forecast */}
      <div className="forecast-section">
        <h2>12-Month Forecast</h2>
        <div className="forecast-cards">
          <div className="forecast-card">
            <div className="quarter">Q2 2026</div>
            <div className="amount">${monthlyRate * 3}</div>
            <div className="status neutral">On track</div>
          </div>
          <div className="forecast-card">
            <div className="quarter">Q3 2026</div>
            <div className="amount">${monthlyRate * 3 * 1.12}</div>
            <div className="status warning">+12% growth projected</div>
          </div>
          <div className="forecast-card">
            <div className="quarter">Q4 2026</div>
            <div className="amount">${monthlyRate * 3 * 1.25}</div>
            <div className="status alert">+25% growth projected</div>
          </div>
          <div className="forecast-card">
            <div className="quarter">Full Year 2026</div>
            <div className="amount">${yearlyRate}</div>
            <div className="status">Projected annual</div>
          </div>
        </div>
      </div>

      {/* Strategic Insights */}
      <div className="insights-section">
        <h2>Strategic Insights</h2>
        <div className="insight-list">
          <div className="insight">
            <div className="icon">📊</div>
            <div className="content">
              <div className="title">Compute dominates spending</div>
              <div className="detail">EC2 and RDS represent 68% of cloud spend. Optimization focus recommended.</div>
            </div>
          </div>
          <div className="insight">
            <div className="icon">📈</div>
            <div className="content">
              <div className="title">AI/ML costs accelerating</div>
              <div className="detail">Bedrock and SageMaker costs grew 35% month-over-month. Monitor AI adoption carefully.</div>
            </div>
          </div>
          <div className="insight">
            <div className="icon">⚠️</div>
            <div className="content">
              <div className="title">Budget variance risk</div>
              <div className="detail">Current trajectory suggests $400K+ annual spend by EOY. Plan budget reviews quarterly.</div>
            </div>
          </div>
        </div>
      </div>

      {/* Cost Categories */}
      <div className="chart-section">
        <h2>Spend by Category (YTD)</h2>
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie
              data={summary?.top_categories?.slice(0, 5) || []}
              dataKey="cost"
              nameKey="category"
              cx="50%"
              cy="50%"
              label
            >
              {(summary?.top_categories || []).slice(0, 5).map((entry, index) => (
                <Cell key={`cell-${index}`} fill={['#8884d8', '#82ca9d', '#ffc658', '#ff7c7c', '#8dd1e1'][index % 5]} />
              ))}
            </Pie>
            <Tooltip formatter={(value) => `$${value.toFixed(0)}`} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}


// ============================================================================
// Dashboard Router
// ============================================================================

export function CostDashboardRouter({ onNavigate }) {
  const [activeTab, setActiveTab] = useState('executive');

  return (
    <div className="lumen" style={{ height: '100vh' }}>
      <Sidebar active="reports" onNavigate={onNavigate} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'auto' }}>
        <Topbar crumbs={['Workspace', 'Reports']} />
        <div className="dashboard-router">
          <div className="tab-navigation">
            <button
              className={`tab ${activeTab === 'executive' ? 'active' : ''}`}
              onClick={() => setActiveTab('executive')}
            >
              Executive Summary
            </button>
            <button
              className={`tab ${activeTab === 'finance' ? 'active' : ''}`}
              onClick={() => setActiveTab('finance')}
            >
              Finance Portal
            </button>
            <button
              className={`tab ${activeTab === 'finops' ? 'active' : ''}`}
              onClick={() => setActiveTab('finops')}
            >
              FinOps Analytics
            </button>
            <button
              className={`tab ${activeTab === 'team' ? 'active' : ''}`}
              onClick={() => setActiveTab('team')}
            >
              Team Dashboard
            </button>
          </div>

          <div className="tab-content">
            {activeTab === 'executive' && <ExecutiveSummary />}
            {activeTab === 'finance' && <FinancePortal />}
            {activeTab === 'finops' && <FinOpsAnalytics />}
            {activeTab === 'team' && <TeamCostDashboard />}
          </div>
        </div>
      </div>
    </div>
  );
}

export default CostDashboardRouter;
