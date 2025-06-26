package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"

	_ "github.com/lib/pq"
	_ "github.com/mattn/go-sqlite3"
)

// QueryRequest represents parameters for fetching contacts
// Filters maps column names to allowed values.
// Search performs a LIKE match on multiple fields.
type QueryRequest struct {
	Search    string              `json:"search"`
	Filters   map[string][]string `json:"filters"`
	SortBy    string              `json:"sort_by"`
	SortOrder string              `json:"sort_order"`
	Limit     int                 `json:"limit"`
	Offset    int                 `json:"offset"`
}

// Response is returned by /contacts
// Contacts is a slice of map[string]interface{} representing each row.
type Response struct {
	Contacts []map[string]any `json:"contacts"`
}

var usePostgres bool

func main() {
	pgDSN := os.Getenv("POSTGRES_DSN")
	var (
		db  *sql.DB
		err error
	)
	if pgDSN != "" {
		usePostgres = true
		db, err = sql.Open("postgres", pgDSN)
	} else {
		dbPath := os.Getenv("CONTACTS_DB")
		if dbPath == "" {
			dir, err2 := os.Getwd()
			if err2 != nil {
				log.Fatalf("getwd: %v", err2)
			}
			dbPath = fmt.Sprintf("%s/contacts.db", dir)
		}
		db, err = sql.Open("sqlite3", dbPath)
	}
	if err != nil {
		log.Fatalf("open db: %v", err)
	}
	defer db.Close()

	if err := ensureTable(db); err != nil {
		log.Fatalf("ensure table: %v", err)
	}

	http.HandleFunc("/contacts", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}
		var req QueryRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		contacts, err := fetchContacts(db, &req)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		json.NewEncoder(w).Encode(Response{Contacts: contacts})
	})

	log.Println("Go contact API running on :8081")
	log.Fatal(http.ListenAndServe(":8081", nil))
}

func fetchContacts(db *sql.DB, req *QueryRequest) ([]map[string]any, error) {
	query := "SELECT * FROM contacts"
	var params []any
	clauses := []string{}
	phCount := 0
	nextPH := func() string {
		phCount++
		if usePostgres {
			return fmt.Sprintf("$%d", phCount)
		}
		return "?"
	}

	for col, values := range req.Filters {
		if len(values) == 0 {
			continue
		}
		if col == "tags" {
			tagParts := make([]string, 0, len(values))
			for _, v := range values {
				if v == "" {
					tagParts = append(tagParts, "(\"tags\" = '' OR \"tags\" IS NULL)")
					continue
				}
				p1, p2, p3, p4 := nextPH(), nextPH(), nextPH(), nextPH()
				params = append(params, v, v+",%", "%,"+v, "%,"+v+",%")
				tagParts = append(tagParts,
					fmt.Sprintf("(\"tags\" = %s OR \"tags\" LIKE %s OR \"tags\" LIKE %s OR \"tags\" LIKE %s)", p1, p2, p3, p4))
			}
			if len(tagParts) > 0 {
				clauses = append(clauses, "("+strings.Join(tagParts, " OR ")+")")
			}
			continue
		}
		ph := make([]string, len(values))
		for i, v := range values {
			ph[i] = nextPH()
			params = append(params, v)
		}
		clauses = append(clauses, fmt.Sprintf("\"%s\" IN (%s)", col, strings.Join(ph, ",")))
	}
	if req.Search != "" {
		searchCols := []string{"first_name", "last_name", "email", "company_name", "company_alias", "job_title", "mobile", "tags"}
		searchParts := make([]string, len(searchCols))
		for i, c := range searchCols {
			searchParts[i] = fmt.Sprintf("\"%s\" LIKE %s", c, nextPH())
			params = append(params, "%"+req.Search+"%")
		}
		clauses = append(clauses, "("+strings.Join(searchParts, " OR ")+" )")
	}
	if len(clauses) > 0 {
		query += " WHERE " + strings.Join(clauses, " AND ")
	}
	if req.SortBy != "" {
		order := "ASC"
		if strings.ToLower(req.SortOrder) == "desc" {
			order = "DESC"
		}
		query += fmt.Sprintf(" ORDER BY \"%s\" %s", req.SortBy, order)
	}
	if req.Limit > 0 {
		query += " LIMIT " + nextPH()
		params = append(params, req.Limit)
		if req.Offset > 0 {
			query += " OFFSET " + nextPH()
			params = append(params, req.Offset)
		}
	} else if req.Offset > 0 {
		if usePostgres {
			query += " OFFSET " + nextPH()
		} else {
			query += " LIMIT -1 OFFSET " + nextPH()
		}
		params = append(params, req.Offset)
	}

	rows, err := db.Query(query, params...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	cols, err := rows.Columns()
	if err != nil {
		return nil, err
	}

	results := []map[string]any{}
	for rows.Next() {
		vals := make([]any, len(cols))
		ptrs := make([]any, len(cols))
		for i := range vals {
			ptrs[i] = &vals[i]
		}
		if err := rows.Scan(ptrs...); err != nil {
			return nil, err
		}
		rowMap := make(map[string]any, len(cols))
		for i, col := range cols {
			val := vals[i]
			if b, ok := val.([]byte); ok {
				rowMap[col] = string(b)
			} else {
				rowMap[col] = val
			}
		}
		results = append(results, rowMap)
	}
	return results, rows.Err()
}

func ensureTable(db *sql.DB) error {
	_, err := db.Exec(`CREATE TABLE IF NOT EXISTS contacts (
                profile_id TEXT PRIMARY KEY
        )`)
	return err
}
