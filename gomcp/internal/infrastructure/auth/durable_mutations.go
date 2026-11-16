package auth

import (
	"context"
	"database/sql"
)

type authQuerier interface {
	Query(string, ...any) (*sql.Rows, error)
}

func readCurrentUser(db authQuerier, subject string, columns ...string) (*User, error) {
	where := "id=$1 OR email=$1"
	if len(columns) > 0 {
		if columns[0] != "id" && columns[0] != "email" {
			return nil, ErrStoreUnavailable
		}
		where = columns[0] + "=$1"
	}
	rows, err := db.Query(`SELECT id,email,display_name,role,active,email_verified,password_hash,verify_token,verify_expiry,created_at,last_login_at,COALESCE(tenant_id,'') FROM users WHERE `+where+` LIMIT 2`, subject)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var match *User
	for rows.Next() {
		if match != nil {
			return nil, ErrStoreUnavailable
		}
		u := new(User)
		var token sql.NullString
		var created, expiry, last storeTime
		if err = rows.Scan(&u.ID, &u.Email, &u.DisplayName, &u.Role, &u.Active, &u.EmailVerified, &u.PasswordHash, &token, &expiry, &created, &last, &u.TenantID); err != nil {
			return nil, err
		}
		if !created.Valid {
			return nil, ErrStoreUnavailable
		}
		u.CreatedAt = created.Time
		u.VerifyToken = token.String
		if expiry.Valid {
			u.VerifyExpiry = &expiry.Time
		}
		if last.Valid {
			u.LastLoginAt = &last.Time
		}
		match = u
	}
	if err = rows.Err(); err != nil {
		return nil, err
	}
	if match == nil {
		return nil, ErrUserNotFound
	}
	return match, nil
}
func readCurrentTenant(db authQuerier, value, column string) (*Tenant, error) {
	if column != "id" && column != "slug" {
		return nil, ErrStoreUnavailable
	}
	rows, err := db.Query(`SELECT id,name,slug,plan_id,COALESCE(stripe_customer_id,''),COALESCE(stripe_sub_id,''),owner_user_id,active,created_at,events_this_month,month_reset_at,custom_max_events,custom_max_scans,custom_max_users,custom_max_sensors FROM tenants WHERE `+column+`=$1 LIMIT 2`, value)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var match *Tenant
	for rows.Next() {
		if match != nil {
			return nil, ErrStoreUnavailable
		}
		t := new(Tenant)
		var created, reset storeTime
		if err = rows.Scan(&t.ID, &t.Name, &t.Slug, &t.PlanID, &t.PaymentCustomerID, &t.PaymentSubID, &t.OwnerUserID, &t.Active, &created, &t.EventsThisMonth, &reset, &t.CustomMaxEvents, &t.CustomMaxScans, &t.CustomMaxUsers, &t.CustomMaxSensors); err != nil {
			return nil, err
		}
		if !created.Valid || !reset.Valid {
			return nil, ErrStoreUnavailable
		}
		t.CreatedAt = created.Time
		t.MonthResetAt = reset.Time
		match = t
	}
	if err = rows.Err(); err != nil {
		return nil, err
	}
	if match == nil {
		return nil, ErrTenantNotFound
	}
	return match, nil
}
func (s *UserStore) mutateUserDurably(subject string, change func(*User) error) error {
	tx, err := s.db.BeginTx(context.Background(), &sql.TxOptions{Isolation: sql.LevelSerializable})
	if err != nil {
		s.unhealthy = true
		return ErrStoreUnavailable
	}
	defer tx.Rollback()
	current, err := readCurrentUser(tx, subject)
	if err == ErrUserNotFound {
		return err
	}
	if err != nil {
		s.unhealthy = true
		return ErrStoreUnavailable
	}
	candidate := cloneUser(current)
	if err = change(candidate); err != nil {
		return err
	}
	result, err := tx.Exec(`UPDATE users SET display_name=$1,role=$2,active=$3,email_verified=$4,password_hash=$5,verify_token=$6,verify_expiry=$7,last_login_at=$8,tenant_id=$9 WHERE id=$10`, candidate.DisplayName, candidate.Role, candidate.Active, candidate.EmailVerified, candidate.PasswordHash, candidate.VerifyToken, candidate.VerifyExpiry, candidate.LastLoginAt, candidate.TenantID, candidate.ID)
	if err != nil {
		s.unhealthy = true
		return ErrStoreUnavailable
	}
	n, err := result.RowsAffected()
	if err != nil || n != 1 {
		s.unhealthy = true
		return ErrStoreUnavailable
	}
	if err = tx.Commit(); err != nil {
		s.unhealthy = true
		return ErrStoreUnavailable
	}
	s.users[candidate.Email] = cloneUser(candidate)
	return nil
}
func (s *TenantStore) mutateTenantDurably(id string, change func(*Tenant) error) error {
	tx, err := s.db.BeginTx(context.Background(), &sql.TxOptions{Isolation: sql.LevelSerializable})
	if err != nil {
		s.unhealthy = true
		return ErrStoreUnavailable
	}
	defer tx.Rollback()
	current, err := readCurrentTenant(tx, id, "id")
	if err == ErrTenantNotFound {
		return err
	}
	if err != nil {
		s.unhealthy = true
		return ErrStoreUnavailable
	}
	candidate := cloneTenant(current)
	if err = change(candidate); err != nil {
		return err
	}
	result, err := tx.Exec(`UPDATE tenants SET name=$1,slug=$2,plan_id=$3,stripe_customer_id=$4,stripe_sub_id=$5,active=$6,events_this_month=$7,month_reset_at=$8,custom_max_events=$9,custom_max_scans=$10,custom_max_users=$11,custom_max_sensors=$12 WHERE id=$13`, candidate.Name, candidate.Slug, candidate.PlanID, candidate.PaymentCustomerID, candidate.PaymentSubID, candidate.Active, candidate.EventsThisMonth, candidate.MonthResetAt, candidate.CustomMaxEvents, candidate.CustomMaxScans, candidate.CustomMaxUsers, candidate.CustomMaxSensors, candidate.ID)
	if err != nil {
		s.unhealthy = true
		return ErrStoreUnavailable
	}
	n, err := result.RowsAffected()
	if err != nil || n != 1 {
		s.unhealthy = true
		return ErrStoreUnavailable
	}
	if err = tx.Commit(); err != nil {
		s.unhealthy = true
		return ErrStoreUnavailable
	}
	s.tenants[id] = cloneTenant(candidate)
	return nil
}
