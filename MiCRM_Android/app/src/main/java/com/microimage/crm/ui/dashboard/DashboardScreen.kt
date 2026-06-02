package com.microimage.crm.ui.dashboard

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import com.microimage.crm.api.RetrofitClient
import com.microimage.crm.model.Proposal
import com.microimage.crm.model.SalesActivity
import com.microimage.crm.model.SalesFunnel
import com.microimage.crm.ui.Screen
import com.microimage.crm.ui.theme.MiRed
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(token: String, navController: NavController) {
    val scope = rememberCoroutineScope()
    val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)
    
    var funnelEntries by remember { mutableStateOf<List<SalesFunnel>>(emptyList()) }
    var proposals by remember { mutableStateOf<List<Proposal>>(emptyList()) }
    var activities by remember { mutableStateOf<List<SalesActivity>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var userRole by remember { mutableStateOf("") }

    LaunchedEffect(Unit) {
        scope.launch {
            try {
                val authHeader = "Token $token"
                val userRes = RetrofitClient.apiService.getCurrentUser(authHeader)
                if (userRes.isSuccessful) {
                    userRole = userRes.body()?.role ?: ""
                }

                val funnelResponse = RetrofitClient.apiService.getSalesFunnel(authHeader)
                val proposalsResponse = RetrofitClient.apiService.getProposals(authHeader)
                val activitiesResponse = RetrofitClient.apiService.getSalesActivities(authHeader)

                if (funnelResponse.isSuccessful) funnelEntries = funnelResponse.body() ?: emptyList()
                if (proposalsResponse.isSuccessful) proposals = proposalsResponse.body() ?: emptyList()
                if (activitiesResponse.isSuccessful) activities = activitiesResponse.body() ?: emptyList()

            } catch (e: Exception) {
                errorMessage = "Failed to load data: ${e.message}"
            } finally {
                isLoading = false
            }
        }
    }

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet {
                Spacer(modifier = Modifier.height(16.dp))
                Text("MiCRM Menu", modifier = Modifier.padding(16.dp), style = MaterialTheme.typography.titleLarge)
                NavigationDrawerItem(label = { Text("Dashboard") }, selected = true, onClick = { scope.launch { drawerState.close() } })
                Divider(modifier = Modifier.padding(vertical = 8.dp))
                NavigationDrawerItem(label = { Text("Customers") }, selected = false, onClick = { navController.navigate(Screen.CustomerList.createRoute(token)) })
                NavigationDrawerItem(label = { Text("Proposals") }, selected = false, onClick = { navController.navigate(Screen.SalesProposal.createRoute(token)) })
                NavigationDrawerItem(label = { Text("Campaigns") }, selected = false, onClick = { navController.navigate(Screen.CampaignList.createRoute(token)) })
            }
        }
    ) {
        Scaffold(
            topBar = {
                TopAppBar(
                    title = {
                        Text(
                            text = "MiCRM",
                            color = MiRed,
                            fontWeight = FontWeight.Bold,
                            fontStyle = FontStyle.Italic,
                            fontSize = 22.sp
                        )
                    },
                    navigationIcon = {
                        IconButton(onClick = { scope.launch { drawerState.open() } }) {
                            Icon(Icons.Default.Menu, contentDescription = "Menu", tint = MiRed)
                        }
                    },
                    actions = {
                        IconButton(onClick = { }) {
                            Icon(Icons.Default.Search, contentDescription = "Search", tint = Color.DarkGray)
                        }
                        Box(
                            modifier = Modifier
                                .padding(end = 12.dp)
                                .size(36.dp)
                                .clip(CircleShape)
                                .background(Color(0xFFE2E8F0))
                        ) {
                            Icon(
                                Icons.Default.Person,
                                contentDescription = "Profile",
                                tint = Color.Gray,
                                modifier = Modifier.align(Alignment.Center).size(24.dp)
                            )
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.White)
                )
            },
            bottomBar = {
                MiBottomNavigation(navController, token)
            },
            floatingActionButton = {
                FloatingActionButton(
                    onClick = { navController.navigate(Screen.SalesActivityCreate.createRoute(token)) },
                    containerColor = Color(0xFF991B1B),
                    contentColor = Color.White,
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier.padding(bottom = 8.dp)
                ) {
                    Icon(Icons.Default.Add, contentDescription = "Add")
                }
            }
        ) { paddingValues ->
            Box(modifier = Modifier.padding(paddingValues).fillMaxSize().background(Color(0xFFF8FAFC))) {
                if (isLoading) {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center), color = MiRed)
                } else if (errorMessage != null) {
                    Text(text = errorMessage!!, color = MaterialTheme.colorScheme.error, modifier = Modifier.align(Alignment.Center).padding(16.dp))
                } else {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(bottom = 16.dp)
                    ) {
                        item {
                            Box(modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp), contentAlignment = Alignment.Center) {
                                Surface(modifier = Modifier.size(32.dp), shape = CircleShape, color = Color(0xFFD9EFFF)) {
                                    Icon(Icons.Default.Refresh, contentDescription = null, tint = Color(0xFF0369A1), modifier = Modifier.padding(6.dp))
                                }
                            }
                        }

                        // Sales Funnel
                        item {
                            SectionHeader(title = "Sales Funnel", actionText = "MONTHLY VIEW")
                            LazyRow(
                                contentPadding = PaddingValues(horizontal = 16.dp),
                                horizontalArrangement = Arrangement.spacedBy(16.dp),
                                modifier = Modifier.fillMaxWidth().height(170.dp)
                            ) {
                                items(funnelEntries) { item ->
                                    FunnelCard(item)
                                }
                                if (funnelEntries.isEmpty()) {
                                    // Mock card if empty to show design
                                    item { MockFunnelCard("LEAD", "1.2M", 42, 65) }
                                    item { MockFunnelCard("NEGOTIATION", "850K", 18, 40) }
                                }
                            }
                        }

                        // Recent Proposals
                        item {
                            SectionHeader(title = "Recent Proposals", actionText = "View All →", onActionClick = {
                                navController.navigate(Screen.SalesProposal.createRoute(token))
                            })
                        }
                        if (proposals.isNotEmpty()) {
                            items(proposals.take(3)) { proposal ->
                                ProposalCard(proposal) {
                                    navController.navigate(Screen.ProposalDetail.createRoute(token, proposal.id))
                                }
                            }
                        } else {
                            // Mock items to show design
                            item { MockProposalCard("PROP-8821", "Enterprise Software Suite", "Global Logistics Inc.", "45,000", "ACCEPTED") }
                            item { MockProposalCard("PROP-8825", "Annual Maintenance", "SME Solutions Manila", "12,500", "SENT") }
                        }

                        // Upcoming Activities
                        item {
                            SectionHeader(title = "Upcoming Activities")
                        }
                        if (activities.isNotEmpty()) {
                            items(activities.take(3)) { activity ->
                                ActivityCard(activity)
                            }
                        } else {
                            // Mock items to show design
                            item { MockActivityCard("24", "Product Demonstration", "Greenfield Residences Group", "14:00", "PRIORITY") }
                            item { MockActivityCard("25", "Follow-up Call", "Marco Polo Hotel Chain", "10:30", "PENDING") }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun SectionHeader(title: String, actionText: String? = null, onActionClick: (() -> Unit)? = null) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(text = title, fontSize = 20.sp, fontWeight = FontWeight.Black, color = Color(0xFF0F172A))
        if (actionText != null) {
            Text(
                text = actionText,
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF991B1B),
                modifier = Modifier.clickable { onActionClick?.invoke() }
            )
        }
    }
}

@Composable
fun FunnelCard(item: SalesFunnel) {
    Card(
        modifier = Modifier.width(260.dp).fillMaxHeight(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFD9EFFF))
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Column {
                    Text(text = item.stage.uppercase(), fontSize = 11.sp, fontWeight = FontWeight.Bold, color = Color(0xFF991B1B).copy(alpha = 0.7f))
                    Text(text = "PHP ${formatAmount(item.retail)}", fontSize = 22.sp, fontWeight = FontWeight.Black, color = Color(0xFF0F172A))
                }
                Surface(modifier = Modifier.size(36.dp), shape = RoundedCornerShape(8.dp), color = Color.White.copy(alpha = 0.5f)) {
                    Icon(Icons.Default.FilterList, contentDescription = null, tint = Color(0xFF991B1B), modifier = Modifier.padding(6.dp))
                }
            }
            Spacer(modifier = Modifier.weight(1f))
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(text = "OPPORTUNITIES", fontSize = 10.sp, fontWeight = FontWeight.Bold, color = Color(0xFF475569))
                Text(text = "${item.probability}%", fontSize = 10.sp, fontWeight = FontWeight.Bold, color = Color(0xFF991B1B))
            }
            Spacer(modifier = Modifier.height(4.dp))
            LinearProgressIndicator(
                progress = item.probability / 100f,
                modifier = Modifier.fillMaxWidth().height(8.dp).clip(CircleShape),
                color = Color(0xFF991B1B),
                trackColor = Color.White.copy(alpha = 0.5f)
            )
        }
    }
}

@Composable
fun MockFunnelCard(stage: String, value: String, count: Int, progress: Int) {
    Card(
        modifier = Modifier.width(260.dp).fillMaxHeight(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFD9EFFF))
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Column {
                    Text(text = stage, fontSize = 11.sp, fontWeight = FontWeight.Bold, color = Color(0xFF991B1B).copy(alpha = 0.7f))
                    Text(text = "PHP $value", fontSize = 22.sp, fontWeight = FontWeight.Black, color = Color(0xFF0F172A))
                }
                Surface(modifier = Modifier.size(36.dp), shape = RoundedCornerShape(8.dp), color = Color.White.copy(alpha = 0.5f)) {
                    Icon(Icons.Default.FilterList, contentDescription = null, tint = Color(0xFF991B1B), modifier = Modifier.padding(6.dp))
                }
            }
            Spacer(modifier = Modifier.weight(1f))
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(text = "$count OPPORTUNITIES", fontSize = 10.sp, fontWeight = FontWeight.Bold, color = Color(0xFF475569))
                Text(text = "$progress%", fontSize = 10.sp, fontWeight = FontWeight.Bold, color = Color(0xFF991B1B))
            }
            Spacer(modifier = Modifier.height(4.dp))
            LinearProgressIndicator(
                progress = progress / 100f,
                modifier = Modifier.fillMaxWidth().height(8.dp).clip(CircleShape),
                color = Color(0xFF991B1B),
                trackColor = Color.White.copy(alpha = 0.5f)
            )
        }
    }
}

@Composable
fun ProposalCard(item: Proposal, onClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 6.dp).clickable { onClick() },
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Surface(color = Color(0xFFF1F5F9), shape = RoundedCornerShape(4.dp)) {
                        Text(text = "#${item.proposalNumber}", modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp), fontSize = 10.sp, fontWeight = FontWeight.Bold, color = Color(0xFF991B1B))
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(text = item.subject, fontWeight = FontWeight.Bold, fontSize = 14.sp, color = Color(0xFF1E293B))
                }
                Text(text = item.customerName, fontSize = 12.sp, color = Color.Gray, modifier = Modifier.padding(top = 4.dp))
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(text = "PHP ${formatAmount(item.totalAmount)}", fontWeight = FontWeight.Black, fontSize = 14.sp, color = Color(0xFF0F172A))
                Surface(
                    modifier = Modifier.padding(top = 4.dp),
                    color = if (item.status.contains("Accepted", true)) Color(0xFFD9F9E6) else Color(0xFFFFEDEB),
                    shape = RoundedCornerShape(4.dp)
                ) {
                    Text(
                        text = item.status.uppercase(),
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Black,
                        color = if (item.status.contains("Accepted", true)) Color(0xFF059669) else Color(0xFFEF4444)
                    )
                }
            }
        }
    }
}

@Composable
fun MockProposalCard(id: String, title: String, client: String, value: String, status: String) {
    Card(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 6.dp),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White)
    ) {
        Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Surface(color = Color(0xFFF1F5F9), shape = RoundedCornerShape(4.dp)) {
                        Text(text = "#$id", modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp), fontSize = 10.sp, fontWeight = FontWeight.Bold, color = Color(0xFF991B1B))
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(text = title, fontWeight = FontWeight.Bold, fontSize = 14.sp, color = Color(0xFF1E293B))
                }
                Text(text = client, fontSize = 12.sp, color = Color.Gray, modifier = Modifier.padding(top = 4.dp))
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(text = "PHP $value", fontWeight = FontWeight.Black, fontSize = 14.sp, color = Color(0xFF0F172A))
                Surface(
                    modifier = Modifier.padding(top = 4.dp),
                    color = if (status == "ACCEPTED") Color(0xFFD9F9E6) else Color(0xFFFFEDEB),
                    shape = RoundedCornerShape(4.dp)
                ) {
                    Text(
                        text = status,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Black,
                        color = if (status == "ACCEPTED") Color(0xFF059669) else Color(0xFFEF4444)
                    )
                }
            }
        }
    }
}

@Composable
fun ActivityCard(item: SalesActivity) {
    Card(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFEDF8FF))
    ) {
        Row(modifier = Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Surface(modifier = Modifier.size(50.dp), shape = RoundedCornerShape(12.dp), color = Color.White) {
                Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                    Text(text = "OCT", fontSize = 9.sp, fontWeight = FontWeight.Bold, color = Color(0xFF991B1B))
                    Text(text = "24", fontSize = 18.sp, fontWeight = FontWeight.Black, color = Color(0xFF0F172A))
                }
            }
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(text = item.title, fontWeight = FontWeight.Bold, fontSize = 14.sp, color = Color(0xFF1E293B))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.AccessTime, contentDescription = null, modifier = Modifier.size(12.dp), tint = Color.Gray)
                        Text(text = " 14:00", fontSize = 10.sp, color = Color.Gray, fontWeight = FontWeight.Bold)
                    }
                }
                Text(text = item.customerName ?: "Internal", fontSize = 12.sp, color = Color.Gray)
                Spacer(modifier = Modifier.height(8.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Row {
                        repeat(2) { Box(modifier = Modifier.size(20.dp).clip(CircleShape).background(Color.Gray).offset(x = (it * -8).dp)) }
                    }
                    Spacer(modifier = Modifier.weight(1f))
                    Surface(color = Color(0xFFFFEDEB), shape = RoundedCornerShape(12.dp)) {
                        Text(text = item.status.uppercase(), modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp), fontSize = 9.sp, fontWeight = FontWeight.Bold, color = Color(0xFF991B1B))
                    }
                }
            }
        }
    }
}

@Composable
fun MockActivityCard(day: String, title: String, client: String, time: String, status: String) {
    Card(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFEDF8FF))
    ) {
        Row(modifier = Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Surface(modifier = Modifier.size(50.dp), shape = RoundedCornerShape(12.dp), color = Color.White) {
                Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                    Text(text = "OCT", fontSize = 9.sp, fontWeight = FontWeight.Bold, color = Color(0xFF991B1B))
                    Text(text = day, fontSize = 18.sp, fontWeight = FontWeight.Black, color = Color(0xFF0F172A))
                }
            }
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(text = title, fontWeight = FontWeight.Bold, fontSize = 14.sp, color = Color(0xFF1E293B))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.AccessTime, contentDescription = null, modifier = Modifier.size(12.dp), tint = Color.Gray)
                        Text(text = " $time", fontSize = 10.sp, color = Color.Gray, fontWeight = FontWeight.Bold)
                    }
                }
                Text(text = client, fontSize = 12.sp, color = Color.Gray)
                Spacer(modifier = Modifier.height(8.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Row {
                        Box(modifier = Modifier.size(20.dp).clip(CircleShape).background(Color.Gray))
                        Box(modifier = Modifier.size(20.dp).offset(x = (-8).dp).clip(CircleShape).background(MiRed))
                    }
                    Spacer(modifier = Modifier.weight(1f))
                    Surface(color = Color(0xFFFFEDEB), shape = RoundedCornerShape(12.dp)) {
                        Text(text = status, modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp), fontSize = 9.sp, fontWeight = FontWeight.Bold, color = Color(0xFF991B1B))
                    }
                }
            }
        }
    }
}

@Composable
fun MiBottomNavigation(navController: NavController, token: String) {
    Surface(modifier = Modifier.fillMaxWidth().height(80.dp), color = Color.White, shadowElevation = 8.dp) {
        Row(modifier = Modifier.fillMaxSize(), horizontalArrangement = Arrangement.SpaceAround, verticalAlignment = Alignment.CenterVertically) {
            MiBottomNavItem(Icons.Default.GridView, "DASHBOARD", true) { }
            MiBottomNavItem(Icons.Default.Group, "CUSTOMERS", false) { navController.navigate(Screen.CustomerList.createRoute(token)) }
            MiBottomNavItem(Icons.Default.Description, "PROPOSALS", false) { navController.navigate(Screen.SalesProposal.createRoute(token)) }
            MiBottomNavItem(Icons.Default.Assignment, "MISSIONS", false) { }
            MiBottomNavItem(Icons.Default.HowToReg, "APPROVALS", false) { }
        }
    }
}

@Composable
fun MiBottomNavItem(icon: ImageVector, label: String, selected: Boolean, onClick: () -> Unit) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
        modifier = Modifier
            .clip(RoundedCornerShape(12.dp))
            .then(if (selected) Modifier.background(Color(0xFFD9EFFF)) else Modifier)
            .clickable { onClick() }
            .padding(horizontal = 12.dp, vertical = 8.dp)
    ) {
        Icon(imageVector = icon, contentDescription = label, tint = if (selected) Color(0xFF991B1B) else Color.Gray, modifier = Modifier.size(22.dp))
        Text(text = label, fontSize = 8.sp, fontWeight = FontWeight.Bold, color = if (selected) Color(0xFF991B1B) else Color.Gray)
    }
}

private fun formatAmount(amount: Double): String {
    return if (amount >= 1_000_000) {
        String.format("%.1fM", amount / 1_000_000)
    } else if (amount >= 1_000) {
        String.format("%.0fK", amount / 1_000)
    } else {
        String.format("%,.0f", amount)
    }
}
