package auth

import "database/sql"

// principalSnapshot serializes local writes and reads current database authority
// when configured. It never substitutes stale RAM after a database error.
func (s *UserStore) principalSnapshot(subject string) (*User, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.unhealthy {
		return nil, ErrStoreUnavailable
	}
	if subject == "" {
		return nil, ErrInvalidToken
	}
	if s.db == nil {
		var match *User
		for _, u := range s.users {
			if u.ID == subject || u.Email == subject {
				if match != nil {
					return nil, ErrInvalidToken
				}
				match = u
			}
		}
		if match == nil {
			return nil, ErrInvalidToken
		}
		return cloneUser(match), nil
	}
	rows, err := s.db.Query(`SELECT id,email,role,COALESCE(tenant_id,''),active FROM users WHERE id=$1 OR email=$1 LIMIT 2`, subject)
	if err != nil {
		s.unhealthy = true
		return nil, ErrStoreUnavailable
	}
	defer rows.Close()
	var match *User
	for rows.Next() {
		if match != nil {
			return nil, ErrInvalidToken
		}
		u := new(User)
		if err = rows.Scan(&u.ID, &u.Email, &u.Role, &u.TenantID, &u.Active); err != nil {
			s.unhealthy = true
			return nil, ErrStoreUnavailable
		}
		match = u
	}
	if rows.Err() != nil {
		s.unhealthy = true
		return nil, ErrStoreUnavailable
	}
	if match == nil {
		return nil, ErrInvalidToken
	}
	return match, nil
}
func (s *TenantStore) principalTenantActive(id string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.unhealthy {
		return ErrStoreUnavailable
	}
	if s.db == nil {
		t, ok := s.tenants[id]
		if !ok || !t.Active {
			return ErrInvalidToken
		}
		return nil
	}
	var active bool
	err := s.db.QueryRow(`SELECT active FROM tenants WHERE id=$1`, id).Scan(&active)
	if err == sql.ErrNoRows {
		return ErrInvalidToken
	}
	if err != nil {
		s.unhealthy = true
		return ErrStoreUnavailable
	}
	if !active {
		return ErrInvalidToken
	}
	return nil
}

// BindPrincipalStores adds live-principal validation to this server-owned JWT
// middleware. NewJWTMiddleware/Verify remain usable as standalone primitives.
func (m *JWTMiddleware) BindPrincipalStores(users *UserStore, tenants *TenantStore) {
	m.resolvePrincipal = func(claims *Claims) (*Claims, error) {
		if users == nil {
			return nil, ErrStoreUnavailable
		}
		u, err := users.principalSnapshot(claims.Sub)
		if err != nil {
			return nil, err
		}
		if !u.Active {
			return nil, ErrInvalidToken
		}
		claimLevel, claimKnown := roleRank[claims.Role]
		ownerLevel, ownerKnown := roleRank[u.Role]
		if !claimKnown || !ownerKnown || claimLevel > ownerLevel || (u.Role == "sensor" && claims.Role != "sensor") {
			return nil, ErrInvalidToken
		}
		switched := claims.TenantID != u.TenantID
		if switched && (claims.Role != "superadmin" || u.Role != "superadmin") {
			return nil, ErrInvalidToken
		}
		if claims.TenantID == "" {
			if claims.Role != "superadmin" || u.Role != "superadmin" {
				return nil, ErrInvalidToken
			}
		} else {
			if tenants == nil {
				return nil, ErrStoreUnavailable
			}
			if err = tenants.principalTenantActive(claims.TenantID); err != nil {
				return nil, err
			}
		}
		copy := *claims
		return &copy, nil
	}
}
