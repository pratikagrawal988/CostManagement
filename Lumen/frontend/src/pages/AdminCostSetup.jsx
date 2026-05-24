/**
 * Admin Cost Management Setup UI
 *
 * Configure AWS CUR ingestion and manage cost data pipelines
 */

import React, { useState, useEffect } from 'react';
import axios from 'axios';

export function AdminCostSetup() {
  const [configs, setConfigs] = useState([]);
  const [jobStatus, setJobStatus] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);

  // Form state for new config
  const [formData, setFormData] = useState({
    tenant_id: 'tenant-demo',
    s3_bucket: '',
    s3_prefix: 'AWSLogs',
    aws_role_arn: '',
    aws_external_id: '',
    enabled: true,
  });

  const [formErrors, setFormErrors] = useState({});
  const [submitLoading, setSubmitLoading] = useState(false);

  useEffect(() => {
    fetchConfigs();
    fetchJobStatus();

    // Refresh every 30 seconds
    const interval = setInterval(() => {
      fetchJobStatus();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const fetchConfigs = async () => {
    try {
      const res = await axios.get('/api/cost/ingest-config');
      setConfigs(res.data.configs || []);
    } catch (error) {
      console.error('Failed to fetch configs:', error);
    }
  };

  const fetchJobStatus = async () => {
    try {
      const res = await axios.get('/api/cost/status', {
        params: { limit: 10 }
      });
      setJobStatus(res.data.job_runs || []);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch job status:', error);
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
    // Clear error for this field
    if (formErrors[name]) {
      setFormErrors(prev => ({
        ...prev,
        [name]: '',
      }));
    }
  };

  const validateForm = () => {
    const errors = {};

    if (!formData.s3_bucket.trim()) {
      errors.s3_bucket = 'S3 bucket name is required';
    }

    if (!formData.aws_role_arn.trim()) {
      errors.aws_role_arn = 'AWS role ARN is required';
    } else if (!formData.aws_role_arn.startsWith('arn:aws:iam::')) {
      errors.aws_role_arn = 'Invalid ARN format';
    }

    if (!formData.aws_external_id.trim()) {
      errors.aws_external_id = 'External ID is required (security best practice)';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleCreateConfig = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setSubmitLoading(true);

    try {
      const response = await axios.post('/api/cost/ingest-config', null, {
        params: {
          tenant_id: formData.tenant_id,
          s3_bucket: formData.s3_bucket,
          s3_prefix: formData.s3_prefix,
          aws_role_arn: formData.aws_role_arn,
          aws_external_id: formData.aws_external_id,
          enabled: formData.enabled,
        }
      });

      // Reset form
      setFormData({
        tenant_id: 'tenant-demo',
        s3_bucket: '',
        s3_prefix: 'AWSLogs',
        aws_role_arn: '',
        aws_external_id: '',
        enabled: true,
      });
      setShowCreateForm(false);

      // Refresh configs
      fetchConfigs();

      alert('Configuration created successfully!');
    } catch (error) {
      alert(`Error creating configuration: ${error.response?.data?.detail || error.message}`);
    } finally {
      setSubmitLoading(false);
    }
  };

  if (loading) return <div className="admin-loading">Loading...</div>;

  return (
    <div className="admin-cost-setup">
      <h1>Cost Management Admin Panel</h1>

      {/* Configurations Section */}
      <section className="configurations-section">
        <div className="section-header">
          <h2>AWS CUR Ingestion Configurations</h2>
          <button
            className="btn btn-primary"
            onClick={() => setShowCreateForm(!showCreateForm)}
          >
            {showCreateForm ? '✕ Cancel' : '+ New Configuration'}
          </button>
        </div>

        {showCreateForm && (
          <div className="create-config-form">
            <h3>Create New Ingest Configuration</h3>

            <div className="form-group">
              <label>Tenant ID</label>
              <input
                type="text"
                name="tenant_id"
                value={formData.tenant_id}
                onChange={handleInputChange}
                disabled
                className="input"
              />
              <small>Identifies the tenant/organization</small>
            </div>

            <div className="form-group">
              <label>S3 Bucket Name *</label>
              <input
                type="text"
                name="s3_bucket"
                placeholder="my-billing-bucket"
                value={formData.s3_bucket}
                onChange={handleInputChange}
                className={`input ${formErrors.s3_bucket ? 'error' : ''}`}
              />
              {formErrors.s3_bucket && (
                <small className="error-text">{formErrors.s3_bucket}</small>
              )}
              <small>Name of the S3 bucket containing CUR files</small>
            </div>

            <div className="form-group">
              <label>S3 Prefix</label>
              <input
                type="text"
                name="s3_prefix"
                placeholder="AWSLogs/123456789012/costs"
                value={formData.s3_prefix}
                onChange={handleInputChange}
                className="input"
              />
              <small>Path prefix for CUR files in S3</small>
            </div>

            <div className="form-group">
              <label>AWS Role ARN *</label>
              <input
                type="text"
                name="aws_role_arn"
                placeholder="arn:aws:iam::123456789012:role/FinOpsServiceRole"
                value={formData.aws_role_arn}
                onChange={handleInputChange}
                className={`input ${formErrors.aws_role_arn ? 'error' : ''}`}
              />
              {formErrors.aws_role_arn && (
                <small className="error-text">{formErrors.aws_role_arn}</small>
              )}
              <small>Cross-account IAM role ARN for S3 access</small>
            </div>

            <div className="form-group">
              <label>External ID *</label>
              <input
                type="text"
                name="aws_external_id"
                placeholder="unique-external-id-12345"
                value={formData.aws_external_id}
                onChange={handleInputChange}
                className={`input ${formErrors.aws_external_id ? 'error' : ''}`}
              />
              {formErrors.aws_external_id && (
                <small className="error-text">{formErrors.aws_external_id}</small>
              )}
              <small>
                Security mechanism to prevent confused deputy problem. Generate unique ID per tenant.
              </small>
            </div>

            <div className="form-group checkbox">
              <label>
                <input
                  type="checkbox"
                  name="enabled"
                  checked={formData.enabled}
                  onChange={handleInputChange}
                />
                Enable ingestion
              </label>
              <small>Disable to pause cost ingestion without deleting configuration</small>
            </div>

            <div className="form-actions">
              <button
                className="btn btn-primary"
                onClick={handleCreateConfig}
                disabled={submitLoading}
              >
                {submitLoading ? 'Creating...' : 'Create Configuration'}
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => setShowCreateForm(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {configs.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">⚙️</div>
            <div className="empty-title">No configurations found</div>
            <div className="empty-description">
              Create your first AWS CUR ingestion configuration to begin tracking cloud costs.
            </div>
          </div>
        ) : (
          <div className="configs-list">
            {configs.map((config) => (
              <div key={config.id} className="config-card">
                <div className="config-header">
                  <div className="config-title">
                    <h3>{config.s3_bucket}</h3>
                    <span className={`status-badge ${config.enabled ? 'active' : 'inactive'}`}>
                      {config.enabled ? '● Active' : '● Disabled'}
                    </span>
                  </div>
                  <div className="config-meta">
                    <span className="tenant-id">Tenant: {config.tenant_id}</span>
                  </div>
                </div>

                <div className="config-details">
                  <div className="detail-row">
                    <span className="label">S3 Prefix:</span>
                    <span className="value">{config.s3_prefix}</span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Role ARN:</span>
                    <span className="value mono">{config.aws_role_arn}</span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Last Tested:</span>
                    <span className="value">
                      {config.last_tested_at
                        ? new Date(config.last_tested_at).toLocaleString()
                        : 'Never'}
                    </span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Test Status:</span>
                    <span className={`badge ${config.test_status}`}>
                      {config.test_status}
                    </span>
                  </div>
                  {config.test_message && (
                    <div className="detail-row">
                      <span className="label">Message:</span>
                      <span className="value">{config.test_message}</span>
                    </div>
                  )}
                </div>

                <div className="config-actions">
                  <button className="btn btn-sm btn-secondary">Edit</button>
                  <button className="btn btn-sm btn-secondary">Test Connection</button>
                  <button className="btn btn-sm btn-danger">Delete</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Job Status Section */}
      <section className="job-status-section">
        <div className="section-header">
          <h2>Job Status & History</h2>
          <button
            className="btn btn-sm btn-secondary"
            onClick={fetchJobStatus}
          >
            ↻ Refresh
          </button>
        </div>

        <div className="job-status-grid">
          {/* Cost Ingest Jobs */}
          <div className="job-group">
            <h3>Cost Ingestion (cost_ingest)</h3>
            <p className="job-description">
              Polls S3 for new CUR files every 5 minutes
            </p>
            {jobStatus
              .filter(job => job.job_name === 'cost_ingest')
              .slice(0, 5)
              .map((job) => (
                <div
                  key={job.id}
                  className={`job-card ${job.status}`}
                >
                  <div className="job-status-badge">{job.status}</div>
                  <div className="job-time">
                    {new Date(job.started_at).toLocaleTimeString()}
                  </div>
                  <div className="job-records">
                    {job.records_processed} records processed
                  </div>
                  {job.duration_seconds && (
                    <div className="job-duration">
                      {job.duration_seconds.toFixed(1)}s
                    </div>
                  )}
                </div>
              ))}
          </div>

          {/* FOCUS Transform Jobs */}
          <div className="job-group">
            <h3>FOCUS Transform (focus_transform)</h3>
            <p className="job-description">
              Transforms raw CUR to FOCUS schema hourly
            </p>
            {jobStatus
              .filter(job => job.job_name === 'focus_transform')
              .slice(0, 5)
              .map((job) => (
                <div
                  key={job.id}
                  className={`job-card ${job.status}`}
                >
                  <div className="job-status-badge">{job.status}</div>
                  <div className="job-time">
                    {new Date(job.started_at).toLocaleTimeString()}
                  </div>
                  <div className="job-records">
                    {job.records_processed} records processed
                  </div>
                  {job.duration_seconds && (
                    <div className="job-duration">
                      {job.duration_seconds.toFixed(1)}s
                    </div>
                  )}
                </div>
              ))}
          </div>
        </div>
      </section>

      {/* Setup Instructions */}
      <section className="setup-instructions">
        <h2>Setup Instructions</h2>

        <div className="instruction-step">
          <div className="step-number">1</div>
          <div className="step-content">
            <h3>Create Cross-Account IAM Role</h3>
            <p>
              In the customer's AWS account, create a role named <code>FinOpsServiceRole</code> with:
            </p>
            <ul>
              <li>Trust relationship to the application's AWS account</li>
              <li>External ID requirement (prevents confused deputy)</li>
              <li>S3 read permissions to the CUR bucket</li>
            </ul>
            <code className="code-block">
{`{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "AWS": "arn:aws:iam::APP_ACCOUNT:role/FinOpsServiceRole"
    },
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": {
        "sts:ExternalId": "unique-id-here"
      }
    }
  }]
}`}
            </code>
          </div>
        </div>

        <div className="instruction-step">
          <div className="step-number">2</div>
          <div className="step-content">
            <h3>Enable AWS CUR</h3>
            <p>
              In AWS Billing console, enable Cost and Usage Report (CUR) with:
            </p>
            <ul>
              <li>Data granularity: Daily</li>
              <li>Compression: Parquet</li>
              <li>Time unit: Daily</li>
              <li>S3 bucket: Your billing bucket</li>
            </ul>
          </div>
        </div>

        <div className="instruction-step">
          <div className="step-number">3</div>
          <div className="step-content">
            <h3>Add Ingest Configuration</h3>
            <p>
              In this admin panel, create a new configuration with:
            </p>
            <ul>
              <li>S3 bucket name (without s3://)</li>
              <li>S3 prefix path (e.g., AWSLogs/123456789012/costs)</li>
              <li>Cross-account role ARN from step 1</li>
              <li>External ID matching the role's condition</li>
            </ul>
          </div>
        </div>

        <div className="instruction-step">
          <div className="step-number">4</div>
          <div className="step-content">
            <h3>Verify & Monitor</h3>
            <p>
              Test the connection and monitor job status:
            </p>
            <ul>
              <li>Click "Test Connection" to verify IAM access</li>
              <li>Monitor job history in the status section above</li>
              <li>Check CostDetail table for ingested records</li>
              <li>Verify FocusCost data after 1+ hours</li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}

export default AdminCostSetup;
